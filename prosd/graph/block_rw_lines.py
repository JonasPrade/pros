import json
import os

from prosd.graph import railgraph, routing
from prosd.models import MasterScenario, RailwayLine, TimetableTrainGroup, RouteTraingroup, ProjectContent, TimetableTrain, RailwayStation, TimetableTrainPart, TimetableCategory
from prosd.manage_db import version
from prosd import db


class BlockRailwayLines:
    def __init__(self, scenario_id):
        self.scenario = MasterScenario.query.get(scenario_id)
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

    def reroute_traingroups(self):
        infra_version = version.Version(scenario=self.scenario)
        route = routing.GraphRoute(graph=self.graph, infra_version=infra_version)

        data = self._read_additional_project_info()

        blocked_ocps = []
        traingroups = []
        following_ocps = dict()
        for key, value in data.items():
            blocked_ocps = []

            pc = ProjectContent.query.get(key)
            infra_version.add_projectcontents_to_version_temporary(
                pc_list=[pc],
                update_infra=True,
                use_subprojects=False
            )
            blocked_ocps.extend([station.db_kuerzel for station in pc.railway_stations])
            blocked_ocps.extend(value["additional_ignore_ocp"])
            traingroups.extend([TimetableTrainGroup.query.get(tg) for tg in value["traingroups_to_reroute"]])
            following_ocps.update(value["following_ocps"])

        traingroups = list(set(traingroups))
        for tg in traingroups:
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
