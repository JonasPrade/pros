import json
import os

from prosd.graph import railgraph, routing
from prosd.models import MasterScenario, MasterArea, RailwayLine, TimetableTrainGroup, RouteTraingroup, ProjectContent, TimetableTrain, RailwayStation, TimetableTrainPart, TimetableCategory, TimetableTrainCost
from prosd.manage_db import version
from prosd import db
from prosd import parameter
from prosd.calculation_methods.base import BaseCalculation


class BlockRailwayLines:
    def __init__(self, scenario_id, reference_scenario_id):
        self.scenario = MasterScenario.query.get(scenario_id)
        self.reference_scenario_id = reference_scenario_id
        self.rg = railgraph.RailGraph()
        self.graph = self.rg.load_graph(self.rg.filepath_save_with_station_and_parallel_connections)
        self.filepath_block = f'../../example_data/railgraph/blocked_scenarios/s-{scenario_id}.json'

    def _save_additional_project_info(self, pc, additional_ignore_ocp, traingroups_to_reroute, following_ocps):
        """

        :param pc:
        :param additional_ignore_ocp: additional ocp that gets ignored for routing
        :return:
        """
        try:
            with open(self.filepath_block, 'r') as openfile:
                geojson_data = json.load(openfile)
        except json.decoder.JSONDecodeError:
            geojson_data = dict()

        geojson_data[pc.id] = {
            "additional_ignore_ocp": additional_ignore_ocp,
            "traingroups_to_reroute": traingroups_to_reroute,
            "following_ocps": following_ocps
        }

        with open(self.filepath_block, 'w') as outfile:
            json.dump(geojson_data, outfile)

    def _read_additional_project_info(self):
        with open(self.filepath_block, 'r') as openfile:
            geojson_data = json.load(openfile)

        return geojson_data

    def _save_geojson(self, additional_project_info):
        with open(self.filepath_block, 'w') as outfile:
            json.dump(additional_project_info, outfile)

    def create_blocking_project(self, from_ocp, to_ocp, project_content_name, stations_via=None, additional_ignore_ocp=None,
                                reroute_train_categories=None, following_ocps=None):
        if reroute_train_categories is None:
            reroute_train_categories = ['sgv', 'spfv']
        if additional_ignore_ocp is None:
            additional_ignore_ocp = []
        if stations_via is None:
            stations_via = []
        if following_ocps is None:
            following_ocps = dict()

        project_content_number = f"s-{self.scenario.id} Sperrung {from_ocp} – {to_ocp}"

        infra_version = version.Version(scenario=self.scenario)
        route = routing.GraphRoute(graph=self.graph, infra_version=infra_version)
        path = route.route_line(station_from=from_ocp, station_to=to_ocp, stations_via=stations_via, save_route=True)

        blocked_lines_id = path['edges']
        blocked_lines = RailwayLine.query.filter(RailwayLine.id.in_(blocked_lines_id)).all()

        blocked_ocp = set()
        blocked_ocp.update(RailwayStation.query.filter(RailwayStation.db_kuerzel.in_(additional_ignore_ocp)).all())

        for stations in [line.stations for line in blocked_lines]:
            for station in stations:
                if station.db_kuerzel == from_ocp or station.db_kuerzel == to_ocp:
                    continue
                blocked_ocp.add(station)

        pc = ProjectContent(
            name=project_content_name,
            project_number=project_content_number,
            closure=True
        )
        pc.railway_lines = blocked_lines
        pc.railway_stations = list(blocked_ocp)
        db.session.add(pc)
        db.session.commit()

        tgs = TimetableTrainGroup.query.join(RouteTraingroup).join(TimetableTrain).join(TimetableTrainPart).join(
            TimetableCategory).filter(
            RouteTraingroup.master_scenario_id == self.scenario.id,
            RouteTraingroup.railway_line_id.in_(blocked_lines_id),
            TimetableCategory.transport_mode.in_(reroute_train_categories)
        ).all()

        tgs_ids = [tg.id for tg in tgs]
        self._save_additional_project_info(pc=pc, additional_ignore_ocp=additional_ignore_ocp, traingroups_to_reroute=tgs_ids, following_ocps=following_ocps)

        return pc

    def delete_blocking_project(self, pc_id):
        infra_version = version.Version(scenario=self.scenario)
        route = routing.GraphRoute(graph=self.graph, infra_version=infra_version)

        pc = ProjectContent.query.get(pc_id)

        additional_information_json = self._read_additional_project_info()
        delete_pc_additional_information = additional_information_json.pop(str(pc_id))
        traingroups = delete_pc_additional_information["traingroups_to_reroute"]

        for tg in traingroups:
            route.line(
                traingroup=TimetableTrainGroup.query.get(tg),
                save_route=True,
                force_recalculation=True
            )

        self._save_geojson(additional_information_json)
        db.session.delete(pc)
        db.session.commit()

    def compare_cost_for_project(self, pc_id):
        pc = ProjectContent.query.get(pc_id)
        additional_data_all = self._read_additional_project_info()
        additional_data_pc = additional_data_all[str(pc_id)]
        traingroups = [TimetableTrainGroup.query.get(tg) for tg in additional_data_pc["traingroups_to_reroute"]]

        disturbance_time_proportion = (365 * parameter.DISTURBANCE_PERCENTAGE)/365

        # route the traingroups
        self._reroute_traingroup(
            pc=pc,
            tgs=traingroups,
            additional_data=additional_data_pc
        )

        road_cost = 0
        wagon_cost = 0
        personnel_cost_train = 0
        train_provision_cost = 0
        areas_resilience_scenario = set()
        areas_reference_scenario = set()
        areas_traingroups_without_sgv = dict()
        for tg in traingroups:
            road_cost += tg.calc_cost_road_transport()
            wagon_cost += tg.wagon_cost_per_day(scenario_id=self.scenario.id)
            personnel_cost_train += tg.personnel_cost_per_day(scenario_id=self.scenario.id)
            train_provision_cost += tg.train_provision_cost_day
            areas = self.get_areas_for_tg(tg)
            areas_resilience_scenario.update(areas["resilience_scenario"])
            areas_reference_scenario.update(areas["reference_scenario"])
            for area in areas["resilience_scenario"]:
                areas_traingroups_without_sgv[area.id] = area.traingroups.copy()
                if tg not in area.traingroups:
                    area.traingroups.append(tg)

        db.session.add_all(areas_resilience_scenario)
        db.session.commit()
        additional_train_costs = wagon_cost + personnel_cost_train + train_provision_cost

        infra_version = version.Version(scenario=self.scenario)
        areas_cost = 0
        for area in areas_resilience_scenario:
            for traction in ['electrification', 'optimised_electrification']:
                area.calculate_infrastructure_cost(
                    traction=traction,
                    infra_version=infra_version,
                    overwrite=True
                )

            for tg in traingroups:
                for traction in ['electrification', 'diesel', 'efuel']:
                    TimetableTrainCost.query.filter(
                        TimetableTrainCost.traingroup_id == tg.id,
                        TimetableTrainCost.master_scenario_id == self.scenario.id,
                        TimetableTrainCost.calculation_method == 'bvwp',  # because sgv
                        TimetableTrainCost.traction == traction  # because sgv uses electrification
                    ).delete()

                    TimetableTrainCost.create(
                        traingroup=tg,
                        master_scenario_id=self.scenario.id,
                        traction=traction,
                        infra_version=infra_version
                    )

            area_cost = area.cost_all_tractions
            areas_cost += area_cost[area.cost_effective_traction]

        # in the area cost, the sgv costs are included. But they use that infrastructure only at disturbance time
        # so this train costs are subtracted
        operating_cost_traingroups_sgv = 0
        for tg in traingroups:
            operating_cost_traingroups_sgv += TimetableTrainCost.query.filter(
                TimetableTrainCost.traingroup_id == tg.id,
                TimetableTrainCost.master_scenario_id == self.scenario.id,
                TimetableTrainCost.calculation_method == 'bvwp',  # because sgv
                TimetableTrainCost.traction == 'electrification'  # because sgv uses electrification
            ).one().cost

        # operating_cost_traingroup, additional_train_cost and road_coast are yearly costs -> calculate sum over duration for price level 2016
        base_calc = BaseCalculation()
        deductible_operating_expenses = base_calc.cost_base_year(
            start_year=parameter.START_YEAR,
            duration=parameter.DURATION_OPERATION,
            cost=operating_cost_traingroups_sgv,
            cost_is_sum=False
        )
        traincost_sgv_day = operating_cost_traingroups_sgv/365 + additional_train_costs
        operating_cost_sgv_resilience_sum = base_calc.cost_base_year(
            start_year=parameter.START_YEAR,
            duration=parameter.DURATION_OPERATION,
            cost=traincost_sgv_day*disturbance_time_proportion*365,
            cost_is_sum=False
        )
        road_cost_sum = base_calc.cost_base_year(
            start_year=parameter.START_YEAR,
            duration=parameter.DURATION_OPERATION,
            cost=road_cost * disturbance_time_proportion*365,  # road cost Tsd. € pro Tag
            cost_is_sum=False
        )

        areas_cost = areas_cost - deductible_operating_expenses
        cost_resilience = areas_cost + operating_cost_sgv_resilience_sum

        area_cost_reference = 0
        for area in areas_reference_scenario:
            area_cost_reference += area.cost_all_tractions[area.cost_effective_traction]

        cost_road_case = area_cost_reference + road_cost_sum

        answer = {}

        answer["road_cost_day"] = road_cost
        answer["road_coast_operation_duration"] = road_cost_sum
        answer["operating_cost_sgv_resilience_day"] = traincost_sgv_day
        answer["operating_cost_sgv_resilience_sum"] = operating_cost_sgv_resilience_sum
        answer["cost_road_case"] = cost_road_case
        answer["cost_resilience"] = cost_resilience

        for area in areas["resilience_scenario"]:
            area.traingroups = areas_traingroups_without_sgv[area.id]

        return answer

    def get_areas_for_tg(self, tg):
        """
        search master_areas where tg runs through
        :param tg:
        :return:
        """
        areas = dict()
        rw_lines = tg.railway_lines_scenario(scenario_id=self.scenario.id)
        areas["resilience_scenario"] = MasterArea.query.filter(
            MasterArea.scenario_id == self.scenario.id,
            MasterArea.superior_master_id == None,
            MasterArea.railway_lines.any(RailwayLine.id.in_([rw.id for rw in rw_lines]))
        ).all()
        areas["reference_scenario"] = MasterArea.query.filter(
            MasterArea.scenario_id == self.reference_scenario_id,
            MasterArea.superior_master_id == None,
            MasterArea.railway_lines.any(RailwayLine.id.in_([rw.id for rw in rw_lines]))
        ).all()

        return areas

    def reroute_traingroups(self):
        infra_version = version.Version(scenario=self.scenario)
        route = routing.GraphRoute(graph=self.graph, infra_version=infra_version)

        data = self._read_additional_project_info()

        blocked_ocps = []
        traingroups = []
        following_ocps = dict()
        for key, additional_data_pc in data.items():
            pc = ProjectContent.query.get(key)
            tgs = [TimetableTrainGroup.query.get(tg) for tg in additional_data_pc["traingroups_to_reroute"]]
            self._reroute_traingroup(pc, tgs, additional_data_pc)

    def _reroute_traingroup(self, pc, tgs, additional_data):
        infra_version = version.Version(scenario=self.scenario)
        route = routing.GraphRoute(graph=self.graph, infra_version=infra_version)
        blocked_ocps = []

        infra_version.add_projectcontents_to_version_temporary(
            pc_list=[pc],
            update_infra=True,
            use_subprojects=False
        )
        blocked_ocps.extend([station.db_kuerzel for station in pc.railway_stations])
        blocked_ocps.extend(additional_data["additional_ignore_ocp"])

        following_ocps = additional_data["following_ocps"]

        for tg in tgs:
            route.line(
                traingroup=tg,
                save_route=True,
                force_recalculation=True,
                ignore_ocps=set(blocked_ocps),
                following_ocps=following_ocps
            )

    def reroute_traingroups_without_blocked_lines(self):
        infra_version = version.Version(scenario=self.scenario)
        data = self._read_additional_project_info()
        traingroups = []
        for key, value in data.items():
            pc = ProjectContent.query.get(key)
            traingroups.extend([TimetableTrainGroup.query.get(tg) for tg in value["traingroups_to_reroute"]])

        route = routing.GraphRoute(graph=self.graph, infra_version=infra_version)
        for tg in traingroups:
            route.line(
                traingroup=tg,
                save_route=True,
                force_recalculation=True
            )
