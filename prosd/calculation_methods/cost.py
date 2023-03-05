import os
import pandas
import logging
import collections
import sqlalchemy
import math
import datetime
import json

from prosd import db
from prosd.models import RailwayLine, RouteTraingroup, VehiclePattern, TimetableOcp, ProjectContent, ProjectGroup, RailwayStation, TimetableTrainCost, TrainCycle, TrainCycleElement, NoTrainCostError, get_calculation_method
from prosd.calculation_methods.base import BaseCalculation
from prosd import parameter


def add_geojson_catenary_too_long(line_id, station_id):
    # TODO: Filepath like graph
    dirname = os.path.realpath(__file__)
    filepath_catenary_too_long = os.path.realpath(
        os.path.join(dirname, '../../../example_data/railgraph/catenary_too_long.json'))

    with open(filepath_catenary_too_long, 'r') as openfile:
        data = json.load(openfile)

    data.append([line_id, station_id])

    with open(filepath_catenary_too_long, 'w') as outfile:
        json.dump(data, outfile)


class BatteryCapacityError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LineNotInRoutError(Exception):
    def __init__(self, message):
        super().__init__(message)


class BvwpCost(BaseCalculation):
    def __init__(self, investment_cost, maintenance_cost, start_year_planning, abs_nbs="abs"):
        # TODO: Change the calculation of that in sepeart funcitons, that is no __init__
        super().__init__()
        self.cost_2015 = None
        self.capital_service_cost_2015 = None
        self.maintenance_cost_2015 = None
        self.investment_cost_2015 = None
        self.planning_cost_2015 = None
        self.BASE_YEAR = parameter.BASE_YEAR
        self.p = parameter.RATE
        self.FACTOR_PLANNING = parameter.FACTOR_PLANNING
        self.DURATION_PLANNING = parameter.DURATION_PLANNING
        self.DURATION_OPERATION = parameter.DURATION_OPERATION # because this is only used for electrification
        self.ANUALITY_FACTOR = parameter.ANUALITY_FACTOR

        self.infrastructure_type = None

        self.duration_build = parameter.DURATION_BUILDING  # TODO That can be rethought
        self.start_year_planning = start_year_planning
        self.start_year_building = self.start_year_planning + self.DURATION_PLANNING
        self.start_year_operation = self.start_year_building + self.duration_build
        self.end_year_operation = self.start_year_operation + self.DURATION_OPERATION

        self.investment_cost = investment_cost
        self.planning_cost = self.investment_cost * self.FACTOR_PLANNING
        self.maintenace_cost = maintenance_cost

    def calc_base_year_cost(self):
        self.planning_cost_2015 = self.cost_base_year(start_year=self.start_year_planning, duration=self.DURATION_PLANNING,
                                                      cost=self.planning_cost)
        self.investment_cost_2015 = self.cost_base_year(start_year=self.start_year_building,
                                                        duration=self.duration_build, cost=self.investment_cost)
        self.maintenance_cost_2015 = self.cost_base_year(start_year=self.start_year_operation,
                                                         duration=self.DURATION_OPERATION, cost=self.maintenace_cost,
                                                         cost_is_sum=False)
        self.capital_service_cost_2015 = self.calc_capital_service_infrastructure(
            investment_cost_2015=self.investment_cost_2015)

        self.cost_2015 = self.planning_cost_2015 + self.investment_cost_2015 + self.maintenance_cost_2015

    def duration_building(self, abs_nbs):
        """
        calculates the duration of building, based on the calculations of the bvwp
        :param abs_nbs:
        :return:
        """
        dirname = os.path.dirname(__file__)
        self.FILEPATH_DURATION_BVWP = os.path.realpath(
            os.path.join(dirname, "settings/duration_build_rail_bvwp.csv"))
        table_duration = pandas.read_csv(self.FILEPATH_DURATION_BVWP, header=0, index_col=0)

        duration_building = self._duration_year(cost_list=table_duration[abs_nbs])

        return duration_building

    def calc_capital_service_infrastructure(self, investment_cost_2015):
        """

        :param investment_cost_2015:
        :return:
        """
        # TODO: Calculate capital service infrastructure
        capital_service_infrastructure = investment_cost_2015 * self.ANUALITY_FACTOR

        return capital_service_infrastructure

    def _duration_year(self, cost_list):
        for index, cost in cost_list.items():
            if self.investment_cost < cost:
                duration_year = index + 1
                break
        return duration_year


class BvwpCostElectrification(BvwpCost):
    # TODO: Think of cost of substation, maybe there is a more specific calculation possible
    def __init__(self, start_year_planning, railway_lines_scope, infra_version, abs_nbs='abs'):
        """
        calculates the cost of a building a catenary for all railway_lines_scope that has no catenary.
        It uses the infra_version (and not the db) to look up what railway_lines have catenary and which do not have catenary.
        :param start_year_planning:
        :param railway_lines_scope:
        :param infra_version:
        :param abs_nbs:
        """
        self.railway_lines_scope = railway_lines_scope
        self.infra_version = infra_version
        self.MAINTENANCE_FACTOR = parameter.MAINTENANCE_FACTOR  # factor from standardisierte Bewertung Tabelle B-19
        self.COST_OVERHEAD_SINGLE_TRACK = parameter.COST_OVERHEAD_ONE_TRACK  # in thousand Euro
        self.COST_OVERHEAD_DOUBLE_TRACK = parameter.COST_OVERHEAD_TWO_TRACKS
        self.infrastructure_type = 'electrification'
        # TODO: Add costs for engineering buildungs (tunnels)

        self.cost_overhead, self.length = self.calc_cost_unelectrified_railway_lines()
        self.cost_substation = 0

        self.investment_cost = self.cost_overhead + self.cost_substation
        self.maintenace_cost = self.investment_cost * self.MAINTENANCE_FACTOR
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)
        super().calc_base_year_cost()

    def calc_cost_unelectrified_railway_lines(self):
        """
        calculates the length of not electrified lines and returns them. if the line has two tracks, it will multiple the length
        :param railway_lines:
        :return:
        """
        cost = 0
        length_no_catenary = 0
        for line in self.railway_lines_scope:
            line_id = line.id
            cost_factor = self.COST_OVERHEAD_SINGLE_TRACK
            factor_length = 1
            line_infraversion = self.infra_version.get_railwayline_model(railwayline_id = line_id)

            if line_infraversion.catenary == False:
                if line_infraversion.number_tracks == 'zweigleisig':
                    cost_factor = self.COST_OVERHEAD_DOUBLE_TRACK
                    factor_length = 2
                else:
                    cost_factor = self.COST_OVERHEAD_SINGLE_TRACK
                cost += line_infraversion.length * cost_factor / 1000
                length_no_catenary += line_infraversion.length * factor_length / 1000

        return cost, length_no_catenary


class BvwpProjectChargingStation(BvwpCost):
    def __init__(self, start_year_planning, station, abs_nbs='abs'):
        """
        calculates the cost of a building a catenary for all railway_lines_scope that has no catenary.
        It uses the infra_version (and not the db) to look up what railway_lines have catenary and which do not have catenary.
        :param start_year_planning:
        :param railway_lines_scope:
        :param infra_version:
        :param abs_nbs:
        """
        self.station = station
        self.maintenance_factor = parameter.MAINTENANCE_FACTOR  # factor from standardisierte Bewertung Tabelle B-19
        self.cost_charging_station = parameter.COST_CHARGING_STATION  # in thousand Euro
        self.infrastructure_type = 'charging_station'

        self.investment_cost = self.cost_charging_station
        self.maintenace_cost = self.investment_cost * self.maintenance_factor
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)
        super().calc_base_year_cost()


class BvwpProjectSmallChargingStation(BvwpCost):
    def __init__(self, start_year_planning, station, abs_nbs='abs'):
        """
        calculates the cost of a building a catenary for all railway_lines_scope that has no catenary.
        It uses the infra_version (and not the db) to look up what railway_lines have catenary and which do not have catenary.
        :param start_year_planning:
        :param railway_lines_scope:
        :param infra_version:
        :param abs_nbs:
        """
        self.station = station
        self.maintenance_factor = parameter.MAINTENANCE_FACTOR  # factor from standardisierte Bewertung Tabelle B-19
        self.cost_charging_station = parameter.COST_SMALL_CHARGING_STATION  # in thousand Euro
        self.infrastructure_type = 'small_charging_station'

        self.investment_cost = self.cost_charging_station
        self.maintenace_cost = self.investment_cost * self.maintenance_factor
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)
        super().calc_base_year_cost()


def _check_if_station_has_charge_or_catenary(station, infra_version):
    station_electrified = False
    if station.charging_station is True:
        station_electrified = True
        return station_electrified

    lines_station = station.railway_lines
    for line_station in lines_station:
        line_infra_version = infra_version.get_railwayline_model(
            railwayline_id=line_station.id
        )
        if line_infra_version.catenary is True:
            station_electrified = True
            break
    return station_electrified


def create_small_charging_station_project_content(station, start_year_planning, infra_version):
    name = f'Small charging station for {station.name}'

    infrastructure_cost = BvwpProjectSmallChargingStation(
        start_year_planning=start_year_planning,
        station=station
    )

    station = infra_version.prepare_commit_pc_stations([station])

    pc = ProjectContent(
        name=name,
        small_charging_station=True,
        railway_stations=station,
        investment_cost=infrastructure_cost.investment_cost_2015,
        planning_cost=infrastructure_cost.planning_cost_2015,
        maintenance_cost=infrastructure_cost.maintenance_cost_2015,
        capital_service_cost=infrastructure_cost.capital_service_cost_2015,
        planned_total_cost=infrastructure_cost.cost_2015
    )

    return pc


def add_small_charging_stations(infra_version, start_ocps, start_year_planning):
    """
    Check if the start_ocp has a charging possibility for that line. If not -> add a small charging station
    :return:
    """
    small_charging_stations = list()
    for ocp in start_ocps:
        station = infra_version.get_railwaystation_model(ocp.station.id)
        station_electrified = _check_if_station_has_charge_or_catenary(station, infra_version=infra_version)
        if station_electrified is False:
            small_charging_station = create_small_charging_station_project_content(
                station=station,
                start_year_planning=start_year_planning,
                infra_version=infra_version
            )
            small_charging_stations.append(small_charging_station)

    return small_charging_stations


class BvwpProjectBattery(BvwpCost):
    def __init__(self, start_year_planning, area, infra_version, abs_nbs='abs', battery_electrify_start_ocps=True):
        self.area = area
        self.infra_version = infra_version
        self.infra_df = infra_version.infra
        self.infrastructure_type = 'battery'
        self.wait_time = parameter.WAIT_TIME
        self.start_year_planning = start_year_planning

        self.project_contents = []
        black_list_train_group = []
        self.start_ocps = set()
        for group in self.area.traingroups:
            if group in black_list_train_group:
                continue
            else:
                tt_line = group.traingroup_lines
                if tt_line:
                    for tg in tt_line.train_groups:
                        black_list_train_group.append(tg)
                        self.start_ocps.add(tg.first_ocp.ocp)
                        self.start_ocps.add(tg.last_ocp.ocp)
                    cycles = tt_line.get_train_cycles_each_starting_ocp()
                    for cycle in cycles:
                        elements = cycle.elements[0:2]
                        trains = [element.train for element in elements]
                        new_projectcontents = self.calculate_infrastructure(trains, tt_line)
                        self.project_contents.extend(new_projectcontents)
                else:
                    logging.error(f'No line for {group}')

        if battery_electrify_start_ocps is True:
            new_projectcontents = add_small_charging_stations(
                infra_version=self.infra_version,
                start_ocps=self.start_ocps,
                start_year_planning=start_year_planning
            )
            if len(new_projectcontents) > 0:
                self.infra_version.add_projectcontents_to_version_temporary(pc_list=new_projectcontents,
                                                                        update_infra=True)
            self.project_contents.extend(new_projectcontents)

        self.investment_cost = 0
        self.maintenance_cost = 0
        for pc in self.project_contents:
            self.investment_cost += pc.investment_cost
            self.maintenance_cost += pc.maintenance_cost

        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenance_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)
        self.cost_2015 = 0
        self.capital_service_cost_2015 = 0
        self.maintenance_cost_2015 = 0
        self.planning_cost_2015 = 0
        self.investment_cost_2015 = 0
        for pc in self.project_contents:
            self.cost_2015 += pc.planned_total_cost
            self.investment_cost_2015 = pc.investment_cost
            self.capital_service_cost_2015 += pc.capital_service_cost
            self.maintenance_cost_2015 += pc.maintenance_cost
            self.planning_cost_2015 += pc.planning_cost

    def calculate_infrastructure(self, trains, tt_line):
        station_to_rlml_ocp = self._get_station_to_railml_ocp(trains=trains)

        # calculate the energy need and if there is a problem with the battery capacity
        cycle_sections, rw_lines = self.calc_energy_demand(trains, station_to_rlml_ocp)
        cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem, energy_needed_multi_cycle = \
            self._calculate_energy_delta(cycle_sections=cycle_sections, trains=trains)

        project_contents_temp = self._create_additional_infrastructure(
            cycle_sections=cycle_sections,
            one_cycle_problem=one_cycle_problem,
            battery_empty=battery_empty,
            multi_cycle_problem=multi_cycle_problem,
            energy_needed_multi_cycle=energy_needed_multi_cycle,
            tt_line=tt_line,
            rw_lines=rw_lines,
            trains=trains
        )
        if project_contents_temp:
            self.infra_version.add_projectcontents_to_version_temporary(pc_list=project_contents_temp, update_infra=True)

        db.session.autoflush = True
        return project_contents_temp

    def calc_energy_demand(self, trains, station_to_rlml_ocp):
        cycle_sections = []

        for train in trains:
            sections, rw_lines = self._group_rw_lines(train, station_to_rlml_ocp)
            count_stations_to_sections = self._add_count_stations_to_sections(line_groups=sections,
                                                                            rw_lines=rw_lines, train=train)
            sections_with_energy = self._calculate_energy_sections(sections=sections, train=train,
                                                                   stations_to_sections=count_stations_to_sections)
            cycle_sections.append(sections_with_energy)

        return cycle_sections, rw_lines

    def _group_rw_lines(self, train, station_to_rlml_ocp):
        """
        This function returns a DataFrame of railwaylines - in order of the use by the train - grouped by their attribute "catenary".
        :param train:
        :return:
        """
        def create_new_section(catenary_value, old_group=None):
            if old_group is None:
                group_id = 0
            else:
                group_id = old_group["group_id"] + 1

            group = {
                "group_id": group_id,
                "catenary": catenary_value,
                "length": 0,
                "railway_lines": [],
                "last_station": None
            }
            return group

        def add_section_to_sections(group, rw_lines_grouped, last_station):
            group["last_station"] = last_station
            rw_lines_grouped.append(group)
            return rw_lines_grouped

        def add_line_to_section(line, group, group_to_lines):
            group["length"] += line.length / 1000
            group["railway_lines"].append(line)

            # add the group id to the rw_lines
            group_to_lines[line.id] = group["group_id"]
            return group, group_to_lines

        rw_lines = self._get_rwlines_for_train(train)
        sections = list()
        sections_to_lines = dict()

        catenary_value = rw_lines.iloc[0][1].catenary  # start value of catenary
        section = create_new_section(catenary_value=catenary_value)

        for index, row in rw_lines.iterrows():
            """
            Go through the railway lines (in order by section) and group them together as long as they have the same attribute value for catenary
            """
            line = row[1]

            # check if the line has stations. if so, remove that from the list. Check how long the train stands there. if it is longer than trigger a cut of the line group
            station_relevant = False
            station_information = None
            station_list = list(set(line.stations).intersection(station_to_rlml_ocp.keys()))
            if len(station_list) == 1:
                station = station_list[0]
                ocp = station_to_rlml_ocp.pop(station)
                timetable = self.__get_timetable(train_part_id = train.train_part.id, ocp_id=ocp.id)
                stop_duration = timetable.scheduled_time.departure_with_day - timetable.scheduled_time.arrival_with_day
                station_charging_point = self.infra_df["railway_stations"][self.infra_df["railway_stations"].railway_station_id == station.id].railway_station_model.iloc[0].charging_station

                if stop_duration.seconds >= 3*60 or station_charging_point:
                    station_relevant=True

                station_information = {
                    "station_id": station.id,
                    "stop_duration": stop_duration,
                    "station_charging_point": station_charging_point
                }

            if catenary_value != line.catenary or station_relevant==True:
                sections = add_section_to_sections(group=section, rw_lines_grouped=sections, last_station=station_information)
                catenary_value = line.catenary
                section = create_new_section(catenary_value=catenary_value, old_group=section)

            section, sections_to_lines = add_line_to_section(line, section, sections_to_lines)

        # Add the latest section to the sections. The ocp is the last ocp of that traingroup
        # therefore the next trains departure at that station must be calculated
        ocp = train.train_group.last_ocp.ocp
        train_traincycleelement = TrainCycleElement.query.join(TrainCycle).filter(
            TrainCycle.trainline_id == train.train_group.traingroup_lines.id,
            TrainCycle.wait_time == self.wait_time,
            TrainCycleElement.train_id == train.id
        ).scalar()
        next_train = TrainCycleElement.query.join(TrainCycle).filter(
            TrainCycle.trainline_id == train.train_group.traingroup_lines.id,
            TrainCycle.wait_time == self.wait_time,
            TrainCycle.id == train_traincycleelement.train_cycle_id,
            TrainCycleElement.sequence == train_traincycleelement.sequence + 1
        ).scalar()
        timetable_train = self.__get_timetable(train_part_id=train.train_part.id, ocp_id=ocp.id)

        if next_train is None:  # in this case there are only two trains in one cycle
            # use a standard value
            # TODO: Find better solution
            stop_duration = datetime.timedelta(hours=1)
        else:
            next_train = next_train.train
            timetable_next_train = self.__get_timetable(train_part_id=next_train.train_part.id, ocp_id=ocp.id)
            stop_duration = timetable_next_train.scheduled_time.departure_with_day - timetable_train.scheduled_time.arrival_with_day

        station = train.train_group.last_ocp.ocp.station
        station_information = {
            "station_id": station.id,
            "stop_duration": stop_duration,
            "station_charging_point": self.infra_df["railway_stations"][
            self.infra_df["railway_stations"].railway_station_id == station.id].railway_station_model.iloc[
            0].charging_station
        }
        sections = add_section_to_sections(group=section, rw_lines_grouped=sections, last_station=station_information)

        # Add the group_id to the railway_lines
        # TODO: That must be m:n
        rw_lines["section_id"] = rw_lines["railway_line_id"].map(sections_to_lines)
        rw_lines = rw_lines.sort_values(by=["sequence"])

        # calculate the duration for each rw_lines_grouped
        for segment in sections:
            segment["duration"] = datetime.timedelta(
                seconds=segment["length"] / train.train_group.travel_speed_average(self.infra_version) * 3600)

        return sections, rw_lines

    def __get_timetable(self, train_part_id, ocp_id):
        try:
            timetable = TimetableOcp.query.filter(sqlalchemy.and_(
                TimetableOcp.train_part == train_part_id,
                TimetableOcp.ocp_id == ocp_id
            )).scalar()
        except sqlalchemy.exc.MultipleResultsFound as e:
            timetables = TimetableOcp.query.filter(sqlalchemy.and_(
                TimetableOcp.train_part == train_part_id,
                TimetableOcp.ocp_id == ocp_id
            )).all()
            for timetable in timetables:
                if timetable.scheduled_time.arrival is not None:
                    break

        return timetable

    def _get_station_to_railml_ocp(self, trains):
        """

        :param traingroup:
        :return:
        """
        traingroup = trains[0].train_group
        train_stations = traingroup.stops
        train_stations.remove(traingroup.first_ocp.ocp)
        train_stations.remove(traingroup.last_ocp.ocp)
        station_to_rlml_ocp = dict()
        for t_ocp in train_stations:
            if t_ocp.station:
                station_to_rlml_ocp[t_ocp.station] = t_ocp
        return station_to_rlml_ocp

    def _get_rwlines_for_train(self, train):
        """
        get the railway_lines of the DataFrame in order of their use by the train.
        Have in mind, that the railway lines DataFrame differs from the database, because some attribute may be changed through former calculations.
        :param train:
        :return:
        """
        tg_id = train.train_group.id
        db.session.autoflush=False  # to protect changes
        order_railway_lines_tuple = db.session.query(RailwayLine.id, RouteTraingroup.section).join(
            RouteTraingroup).filter(
                RouteTraingroup.traingroup_id == tg_id,
                RouteTraingroup.master_scenario_id == self.infra_version.scenario.id
            ).order_by(RouteTraingroup.section).all()
        db.session.autoflush = True
        order_railway_lines = []

        line_to_sequence = dict()
        for entry in order_railway_lines_tuple:
            line_id = entry[0]
            sequence = entry[1]
            order_railway_lines.append(line_id)
            line_to_sequence[line_id] = sequence

        rw_lines = self.infra_df["railway_lines"][self.infra_df["railway_lines"]["railway_line_id"].isin(order_railway_lines)]
        rw_lines.insert(2, "sequence", rw_lines["railway_line_id"].map(line_to_sequence))
        # rw_lines["sequence"] = rw_lines["railway_line_id"].map(line_to_sequence)
        rw_lines = rw_lines.sort_values(by=["sequence"])

        return rw_lines

    def _calculate_energy_sections(self, sections, train, stations_to_sections):
        """
        calculate the needed energy in relation to the battery for a train
        :return:
        """
        # calculate for each rw_lines_ordered the energy needed and battery level

        if train.train_part.formation.formation_calculation_standi:
            vehicles = train.train_part.formation.formation_calculation_standi.vehicles
        else:
            vehicles = train.train_part.formation.vehicles

        for section in sections:
            energy_sum_group = 0
            energy_running_group = 0
            energy_stops_group = 0
            for vehicle in vehicles:
                vehicle_pattern = VehiclePattern.query.get(vehicle.vehicle_pattern.vehicle_pattern_id_battery)
                length = section["length"]
                count_stops = stations_to_sections[section["group_id"]]

                # calculate the energy used by running for this group
                if section["catenary"] == False:
                    additional_battery = vehicle_pattern.additional_energy_without_overhead*(train.train_group.length_line_no_catenary(self.infra_version)/train.train_group.length_line(self.infra_version.scenario.id))
                else:
                    additional_battery = 0

                energy_per_km = vehicle_pattern.energy_per_km
                energy_running = (1 + additional_battery) * energy_per_km * length

                # calculate the energy needed for the stops (acceleration etc.)
                energy_stops = self._calc_energy_stops(vehicle_pattern=vehicle_pattern, count_stops=count_stops,
                                                       train_group=train.train_group)

                energy_sum_group += energy_running + energy_stops
                energy_running_group += energy_running
                energy_stops_group += energy_stops

            section["energy"] = energy_sum_group
            section["energy_running"] = energy_running_group
            section["energy_stops"] = energy_stops_group

        return sections

    def _calc_energy_stops(self, vehicle_pattern, count_stops, train_group):
        """
        calculates the energy needed for stops at a group of lines (nach Verfahrensanleitung Standi)
        :param line_group:
        :param vehicle_pattern:
        :return:
        """
        intermediate_1 = 55.6 * (
                train_group.travel_time.total_seconds() / 60 - train_group.stops_duration.total_seconds() / 60)
        segments = train_group.stops_count - 1
        try:
            reference_speed = 3.6 / (vehicle_pattern.energy_stop_a * segments) * (intermediate_1 - math.sqrt(
                intermediate_1 ** 2 - 2 * vehicle_pattern.energy_stop_a * segments * (
                            train_group.length_line(self.infra_version.scenario.id) * 1000)))
        except ValueError:
            logging.info(
                f'Could not calculate reference speed for train_group {train_group}. More information on page 197 Verfahrensanleitung Standardisierte Bewertung')
            reference_speed = 160
        energy_per_stop = vehicle_pattern.energy_stop_b * (reference_speed ** 2) * vehicle_pattern.weight * (10 ** (-6))
        energy_stops = energy_per_stop * count_stops

        return energy_stops

    def _add_count_stations_to_sections(self, line_groups, rw_lines, train):
        """
        calculates the count of stops of a line group. That is needed for the energy calculation
        :return:
        """
        stops = train.train_group.stops
        stops_to_groups = dict()
        length_line = train.train_group.length_line
        travel_time = train.train_group.travel_time
        first_departure = train.train_group.first_ocp.scheduled_time.departure_with_day

        for stop in stops:
            if stop.station:
                lines_of_stations = [line.id for line in stop.station.railway_lines]
                possible_sections = set(
                    rw_lines[rw_lines["railway_line_id"].isin(lines_of_stations)]["section_id"].to_list())
                if len(possible_sections) > 1:
                    # there is more than one group possible
                    # check if only one has catenary
                    group_list = list()
                    for group in line_groups:
                        group_id = group["group_id"]
                        if group_id in possible_sections and group["catenary"] == True:
                            group_list.append(group_id)

                    group_list = sorted(group_list)

                    if len(group_list) >= 1:
                        stops_to_groups[stop.id] = group_list[0]

                elif len(possible_sections) == 1:
                    stops_to_groups[stop.id] = possible_sections.pop()
                else:
                    logging.error(f"Possible Groups has a non valid length {possible_sections}")
            else:
                logging.debug(f"OCP {stop} not found in infrastructure database. Calculate this stop manual.")
                # get the arrival at the station
                tt_ocp = TimetableOcp.query.filter(
                    sqlalchemy.and_(
                        TimetableOcp.ocp_id == stop.id,
                        TimetableOcp.train_part == train.train_part.id
                    )
                ).one()
                arrival = tt_ocp.scheduled_time.arrival_with_day
                # calculate the travel time proportion between travel time to ocp in relation to complete travel_time
                travel_time_to_tt_ocp = arrival - first_departure
                travel_time_proportion = travel_time_to_tt_ocp / travel_time

                # assign the station to that group of railway_lines, that end-kilometer (in proportion to complete
                # length of line) is smaller then the travel_time_proportion
                start_km_group = 0  # because the groups just contain the relative length, the start_position must be added
                for group in line_groups:
                    proportion_km = (start_km_group + group["length"] / 1000) / length_line(self.infra_version.scenario.id)

                    if travel_time_proportion > proportion_km:
                        start_km_group += group["length"] / 1000
                        continue
                    else:
                        stops_to_groups[stop.id] = group["group_id"]
                        break

        count_stations_groups = collections.Counter(stops_to_groups.values())
        return count_stations_groups

    def _calculate_energy_delta(self, cycle_sections, trains):
        """
        calculates the input and output of energy for the line groups.
        :param rw_lines_grouped:
        :param train:
        :return:
        """
        CHARGE = parameter.CHARGE
        battery_capacity = self._calc_battery_capacity(trains)

        battery_status = battery_capacity
        battery_empty = []
        for index, segment in enumerate(cycle_sections):
            train = trains[index]
            arrival_last_ocp = train.train_part.last_ocp.scheduled_time.arrival_with_day

            for index_section, section in enumerate(segment):
                if section["catenary"] == True:
                    duration = section["duration"]
                    charge = CHARGE * (
                                duration.seconds / 3600) + battery_status
                    battery_status = min(battery_capacity, charge)
                    section["battery_after_group"] = battery_status
                else:
                    battery_status = battery_status - section["energy"]
                    section["battery_after_group"] = battery_status

                # add energy to battery if there is a charging station
                if section["last_station"]:
                    if section["last_station"]["station_charging_point"] is True and index_section != len(segment) - 1:
                        # the last segment has to be calculated the duration of standing first before there can be added a charge
                        charge = CHARGE * (section["last_station"]["stop_duration"].seconds/3600) + battery_status
                        battery_status = min(battery_status, charge)

                if battery_status < 0:
                    charge_time_needed = datetime.timedelta(hours=abs(battery_status/CHARGE))
                    battery_empty.append({"cycle_index": index, "section_index": index_section, "battery_status": battery_status, "charge_time_needed": charge_time_needed})

            # add the time that the vehicle stands at the end of a segment
            if index != len(
                    cycle_sections) - 1:  # so in this case, there is a following segment of the train cycle
                departure_next_segment = trains[index + 1].train_part.first_ocp.scheduled_time.departure_with_day
            else:
                departure_next_segment = trains[1].train_part.first_ocp.scheduled_time.departure_with_day

            stand_time = arrival_last_ocp - departure_next_segment

            if segment[-1]["catenary"] is True or segment[-1]["last_station"]["station_charging_point"] is True:  # this is the latest line_group of the segment
                charge = CHARGE * (stand_time.seconds / 60) + battery_status
                battery_status = min(battery_capacity, charge)
                # TODO: Add that to information to the cycle_lines_grouped

        # check if the energy is enough for on cycle
        if len(battery_empty) > 0:
            one_cycle_problem = True
        else:
            one_cycle_problem = False

        # checks if the battery runs empty over multiple cycles. If yes, it sets the multi_cycle_problem variable to
        # True
        battery_delta = battery_capacity - battery_status
        if battery_delta != 0:
            possible_cycles = battery_capacity / battery_delta
            needed_cycles = int(len(TrainCycle.get_train_cycles(
                timetableline_id = train.train_group.traingroup_lines.id,
                wait_time=self.wait_time
            )[0].elements)/2)
            if possible_cycles < needed_cycles:
                multi_cycle_problem = True
                allowed_minimal_battery_status = battery_capacity - battery_capacity/needed_cycles
                energy_needed_multi_cycle = allowed_minimal_battery_status - battery_status
            else:
                multi_cycle_problem = False
                energy_needed_multi_cycle = None
        else:
            multi_cycle_problem = False
            energy_needed_multi_cycle = None

        return cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem, energy_needed_multi_cycle

    def _create_additional_infrastructure(self, cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem, energy_needed_multi_cycle, tt_line, rw_lines, trains):
        new_projects = []

        additional_charge_one_cycle_problem = 0
        battery_capacity = self._calc_battery_capacity(trains)
        if one_cycle_problem is True:
            forward = False
            backwards = False
            forward_energy_needed = 0
            backward_energy_needed = 0
            for empty in battery_empty:
                if empty["cycle_index"] == 0:
                    forward = True
                    forward_energy_needed = max(forward_energy_needed, abs(empty["battery_status"]))

                if empty["cycle_index"] == 1:
                    backwards = True
                    backward_energy_needed = max(backward_energy_needed, abs(empty["battery_status"]))

            if backwards is True:
                pc, possible_charge = self._create_infrastructure_point(cycle_sections[0][-1], battery_capacity)
                if pc is not None:
                    additional_charge = min(battery_capacity, cycle_sections[0][-1]["battery_after_group"] + possible_charge)-cycle_sections[0][-1]["battery_after_group"]
                    additional_charge_one_cycle_problem += additional_charge
                    backwards = False
                    new_projects.append(pc)
                    for section in cycle_sections[1]:
                        section["battery_after_group"] = min(battery_capacity, section["battery_after_group"] + additional_charge)
                        if section["battery_after_group"] < 0:
                            backwards = True

            if forward is True:
                possible_lines_id = []
                for section_index, section in enumerate(cycle_sections[0]):
                    forward = False
                    backwards = False
                    possible_lines_id.extend([line.id for line in section["railway_lines"]])
                    if section["battery_after_group"] > 0:
                        continue
                    pc, charge_needed = self._electrify_additional_railwaylines(tt_line, rw_lines, forward_energy_needed, possible_lines_id, battery_capacity)
                    energy_possible = forward_energy_needed - charge_needed
                    additional_charge_one_cycle_problem += energy_possible
                    for segment_index, segment in enumerate(cycle_sections):
                        for section in segment:
                            if segment_index == 0 and section_index > section["group_id"]:
                                continue
                            section["battery_after_group"] = min(battery_capacity, section["battery_after_group"] + energy_possible)
                            if section["battery_after_group"] < 0:
                                if segment_index == 0:
                                    forward = True
                                if segment_index == 1:
                                    backwards = True
                    new_projects.append(pc)
                    if forward is False and backwards is False:
                        break
            if forward is True:
                logging.error(f"For {tt_line} there is not enough infrastructure for the first way. Therefore there is actually no solution programmed.")

            if backwards is True:
                logging.error(f"For {tt_line} there is a one_cycle_problem on the backward path which can't be solved yet")

        if multi_cycle_problem is True:
            energy_needed_multi_cycle -= additional_charge_one_cycle_problem

            # infrastructure endpoint
            if energy_needed_multi_cycle > 0:
                projects, energy_needed_multi_cycle = self._create_infrastructure_endpoints(cycle_sections, energy_needed_multi_cycle, battery_capacity)
                new_projects.extend(projects)

            # charging stations between
            if energy_needed_multi_cycle > 0:
                projects, energy_needed_multi_cycle = self._create_infrastructure_interstations(cycle_sections, energy_needed_multi_cycle, battery_capacity)
                new_projects.extend(projects)

            # additional railway_infrastructure
            if energy_needed_multi_cycle > 0:
                possible_lines_id = []
                for section in cycle_sections[0]:
                    if section["catenary"] is False:
                        possible_lines_id.extend([line.id for line in section["railway_lines"]])

                project, energy_needed_multi_cycle = self._electrify_additional_railwaylines(tt_line=tt_line,
                                                                                              rw_lines=rw_lines,
                                                                                              charge_needed=energy_needed_multi_cycle,
                                                                                              possible_lines_id=possible_lines_id,
                                                                                              battery_capacity=battery_capacity)
                new_projects.append(project)

            if energy_needed_multi_cycle > 0:
                raise BatteryCapacityError(
                    f"For {tt_line} there couldn't be installed enough infrastructure for multi_cycle_problem"
                )

        return new_projects

    def _create_infrastructure_endpoints(self, cycle_sections, charge_needed, battery_capacity):
        """
        :param cycle_sections:
        :param charge_needed:
        :return:
        """
        energy_one_way_problem = False
        energy_cycle_problem = False
        new_project_contents = list()
        PROJECT_GROUP = ProjectGroup.query.get(4)

        new_projects = []
        for segment in cycle_sections:
            pc, possible_charge = self._create_infrastructure_point(segment[-1], battery_capacity)
            if pc is not None:
                charge_needed = charge_needed - possible_charge
                if charge_needed < 0:
                    return new_projects, charge_needed
                new_projects.append(pc)

        return new_projects, charge_needed

    def _create_infrastructure_point(self, section, battery_capacity):
        project_load = None
        possible_charge = 0
        ocp_last_section = section["last_station"]
        if section["catenary"] is False and (
                ocp_last_section["station_charging_point"] is None or ocp_last_section[
            "station_charging_point"] is False):
            project_load, possible_charge = self.create_charging_or_catenary_station(
                station_id=ocp_last_section["station_id"],
                line=section["railway_lines"][-1],
                duration_stop=ocp_last_section["stop_duration"]
            )

        possible_charge = min(battery_capacity, possible_charge + section["battery_after_group"])
        return project_load, possible_charge

    def _create_infrastructure_interstations(self, cycle_sections, charge_needed, battery_capacity):
        """
        create charging possibility at interstations where the train stops long enough
        :param cycle_sections:
        :return:
        """
        new_projects = []
        for segment in cycle_sections:
            for section in segment[:-1]:  # get all sections without the last section
                pc, possible_charge = self._create_infrastructure_point(section, battery_capacity)
                if pc is not None:
                    new_projects.append(pc)
                    charge_needed = charge_needed - possible_charge
                    if charge_needed < 0:
                        return new_projects, charge_needed

        return new_projects, charge_needed

    def _electrify_additional_railwaylines(self, tt_line, rw_lines, charge_needed, possible_lines_id, battery_capacity):
        """
        electrify railwaylines so there is no energy problem left anymore
        :param one_cycle_problem:
        :param battery_empt:
        :param multi_cycle_problem:
        :param multi_cycle_allowed_delta:
        :return:
        """
        # PART 1: get lines for electrification
        # try to electrify additional railway_lines
        rw_line_after_usage = db.session.query(RailwayLine, sqlalchemy.func.count(RouteTraingroup.id)).join(RouteTraingroup).filter(
            RailwayLine.id.in_(possible_lines_id),
            RouteTraingroup.master_scenario_id == self.infra_version.scenario.id
        ).group_by(RailwayLine).order_by(sqlalchemy.func.count(RouteTraingroup.id).desc(), RailwayLine.length.asc()).all()

        count_traingroup_max = rw_line_after_usage[0][1]
        rw_line_after_usage = {row[0]:row[1] for row in rw_line_after_usage}
        lines_most_usage = dict()

        # PART 2
        # lines_connected_to_electrification = set()
        lines_connected_to_usage = dict()
        for line, count_traingroup in rw_line_after_usage.items():
            add_line = False
            line_infra_version = self.infra_version.get_railwayline_model(line.id)
            count_traingroup_line = count_traingroup
            if count_traingroup == count_traingroup_max:
                lines_most_usage[line_infra_version] = count_traingroup_max
            # check if a station of that line has a charging possibility or if any line in the station has a catenary
            for station in line_infra_version.stations:
                station_version = self.infra_version.get_railwaystation_model(station.id)
                add_line = _check_if_station_has_charge_or_catenary(station_version, infra_version=self.infra_version)

            # check if a neighbour railway_line has a catenary
            if add_line is False:
                add_line = self._check_if_neighbour_line_has_catenary(line_infra_version)

            if add_line is True:
                # lines_connected_to_electrification.add(line_infra_version)
                lines_connected_to_usage[line_infra_version] = count_traingroup_line

        # If lines_most_usage is empty, take the rw_line_after as lines_most_usage
        if len(lines_connected_to_usage) == 0:
            lines_connected_to_usage = lines_most_usage
            # lines_connected_to_electrification = list(lines_connected_to_electrification)

        # PART 3
        # calculate the duration while running on that line
        lines_to_electrify = set()
        average_speed = tt_line.length_line(self.infra_version.scenario.id) / (tt_line.running_time.seconds/3600)
        while lines_connected_to_usage:
            line = max(lines_connected_to_usage, key=lines_connected_to_usage.get)
            lines_connected_to_usage.pop(line, None)
            # get the lines that are used most and electrify that
            running_time = datetime.timedelta(seconds=((line.length/1000) / average_speed)*3600)
            charge_possible = min((running_time.seconds/3600) * parameter.CHARGE, battery_capacity)
            lines_to_electrify.add(line)
            charge_needed = charge_needed - charge_possible
            if charge_needed < 0:
                if charge_needed < -100:
                    logging.warning(f'For {tt_line} too much elecitrification {charge_needed}kWh')
                break

            # check if the neighbour lines are also in the most used list. If yes -> add that to lines_connect_to_electrification
            try:
                sequence_in_rw_lines = rw_lines[rw_lines["railway_line_id"] == line.id].sequence.tolist()[0]
            except IndexError:
                raise LineNotInRoutError(
                    f"{line.id} not found in the route of train_line {tt_line}. Try reroute"
                )
            neighbour_lines = self._get_neighbour_lines_of_traingroup(sequence_in_rw_lines, rw_lines)
            for line in neighbour_lines:
                try:
                    lines_connected_to_usage[line] = rw_line_after_usage[line]
                except KeyError:
                    logging.info(f"Railway_Line {line} not part of route for train_line {tt_line}")

        # If that is not enough: Find next package of lines if that is not enough

        pc = self.create_electrification(lines=list(lines_to_electrify))

        return pc, charge_needed

    def _get_neighbour_lines_of_traingroup(self, sequence_in_rw_lines, rw_lines):
        lines = []
        next_line = rw_lines[rw_lines["sequence"] == sequence_in_rw_lines + 1].railway_line_id.tolist()
        previous_line = rw_lines[rw_lines["sequence"] == sequence_in_rw_lines -1].railway_line_id.tolist()
        if len(next_line) == 1:
            next_line = next_line[0]
            next_line = self.infra_version.get_railwayline_model(next_line)
            lines.append(next_line)
        if len(previous_line) == 1:
            previous_line = previous_line[0]
            previous_line = self.infra_version.get_railwayline_model(previous_line)
            lines.append(previous_line)

        return lines

    def _check_if_neighbour_line_has_catenary(self, line):
        catenary = False
        neighbour_lines = line.get_neighbouring_lines
        for neighbour_line in neighbour_lines:
            neighbour_line_infra_version = self.infra_version.get_railwayline_model(railwayline_id=neighbour_line.id)
            if neighbour_line_infra_version.catenary is True:
                catenary = True
                break

        return catenary

    def _get_needed_duration_for_charging(self, energy_needed):
        duration = datetime.timedelta(seconds=energy_needed/parameter.CHARGE*3600)
        return duration

    def create_charging_or_catenary_station(self, station_id, duration_stop, line):
        """
        Checks if there is a catenary at other track at this station. If yes -> create electrification project
        If not -> create charging station
        :param station_id:
        :param duration_stop:
        :param line: the line that the train uses last before getting to the station. This line may get electrified
        :return:
        """
        charge = parameter.CHARGE
        charge_while_stop = charge*(duration_stop.seconds/3600)
        line = self.infra_version.get_railwayline_model(line.id)

        station = RailwayStation.query.get(station_id)
        station_catenary_exists = False
        for line_db in station.railway_lines:
            line_station = self.infra_version.get_railwayline_model(line_db.id)
            if line_station.catenary is True:
                station_catenary_exists = True
                break

        if station_catenary_exists is True:
            pc = self.create_catenary_at_station_project_content(station=station, line=line)
        else:
            pc = self.create_charging_project_content(station=station)

        return pc, charge_while_stop

    def create_catenary_at_station_project_content(self, station, line):
        """
        Create a catenary at the railwayline that represents the station
        :param line:
        :return:
        """
        if line.length > 1000:
            add_geojson_catenary_too_long(line.id, station.id)
            logging.info(f"Catenary in {station.name} for {line.id} is too long {line.length}m")

        name = f"Catenary in {station.name} for {line.id}"
        description = f"Oberleitung in {station.name} für die RailwayLine {line.id}"

        infrastructure_cost = BvwpCostElectrification(
            start_year_planning=self.start_year_planning,
            railway_lines_scope=[line],
            infra_version=self.infra_version
        )

        line = self.infra_version.prepare_commit_pc_railway_lines(lines=[line])

        pc = ProjectContent(
            name=name,
            description=description,
            elektrification=True,
            railway_lines=line,
            investment_cost=infrastructure_cost.investment_cost_2015,
            planning_cost=infrastructure_cost.planning_cost_2015,
            maintenance_cost=infrastructure_cost.maintenance_cost_2015,
            capital_service_cost=infrastructure_cost.capital_service_cost_2015,
            planned_total_cost=infrastructure_cost.cost_2015
        )

        return pc

    def create_electrification(self, lines):
        name = f"Electrification for battery case for master_area {self.area.id}"
        description = f"Oberleitung für Batteriefall Untersuchunsgebiet {self.area.id}"

        infrastructure_cost = BvwpCostElectrification(
            start_year_planning=self.start_year_planning,
            railway_lines_scope=lines,
            infra_version=self.infra_version
        )

        lines = self.infra_version.prepare_commit_pc_railway_lines(lines)

        pc = ProjectContent(
            name=name,
            description=description,
            elektrification=True,
            railway_lines=lines,
            investment_cost=infrastructure_cost.investment_cost_2015,
            planning_cost=infrastructure_cost.planning_cost_2015,
            maintenance_cost=infrastructure_cost.maintenance_cost_2015,
            capital_service_cost=infrastructure_cost.capital_service_cost_2015,
            planned_total_cost=infrastructure_cost.cost_2015
        )

        return pc

    def _calc_battery_capacity(self, trains):
        if trains[0].train_part.formation.formation_calculation_standi:
            vehicles = trains[0].train_part.formation.formation_calculation_standi.vehicles
        else:
            vehicles = trains[0].train_part.formation.vehicles

        battery_capacity = 0
        for vehicle in vehicles:
            vehicle_pattern = VehiclePattern.query.get(vehicle.vehicle_pattern.vehicle_pattern_id_battery)
            battery_capacity += vehicle_pattern.battery_capacity  # TODO: Add correct battery_capacity to battery vehicle patterns

        return battery_capacity

    def create_charging_project_content(self, station):
        """
        Create a project_content with a charging point at a specific station
        :return:
        """
        name = f"Ladestation {station.name}"
        description=f"Erstelle Ladestation in {station.name}"

        infrastructure_cost = BvwpProjectChargingStation(
            start_year_planning=self.start_year_planning,
            station=station
        )

        station = self.infra_version.prepare_commit_pc_stations([station])

        pc = ProjectContent(
            name=name,
            description=description,
            charging_station=True,
            railway_stations=station,
            investment_cost=infrastructure_cost.investment_cost_2015,
            planning_cost=infrastructure_cost.planning_cost_2015,
            maintenance_cost=infrastructure_cost.maintenance_cost_2015,
            capital_service_cost=infrastructure_cost.capital_service_cost_2015,
            planned_total_cost=infrastructure_cost.cost_2015
        )

        # the pc is not added to the database yet, because it use case has still to be proven.

        return pc


class BvwpProjectOptimisedElectrification(BvwpCost):
    def __init__(self, start_year_planning, area, infra_version, abs_nbs='abs'):
        self.infrastructure_type = 'optimised_electrification'

        self.start_year_planning = start_year_planning
        self.area = area
        self.sub_areas = area.sub_master_areas
        self.infra_version = infra_version

        self.cost = 0

        self.investment_cost = []
        self.maintenance_cost = []

        if len(self.sub_areas) == 0:
            self.logging(f"No subareas found for {area}. Start calculating subareas")
            self.area.create_sub_areas()
            self.sub_areas = self.area.sub_master_areas

        self._electrify_complete_infra()
        self.traingroup_to_traction = {traingroup: "electrification" for traingroup in self.area.traingroups}
        sub_area_by_length = self._sort_sub_areas_by_usage()
        sub_area_cost = self._calculate_optimisation(sub_area_by_length)

        self.start_ocps = set()
        for tg in self.area.traingroups:
            self.start_ocps.add(tg.first_ocp.ocp)
            self.start_ocps.add(tg.last_ocp.ocp)

        self.investment_cost = 0
        self.maintenance_cost = 0
        self.planning_cost = 0
        self.project_contents = []

        # add small charging stations to starting ocps if there is no charging possibility there.
        small_charging_projects = add_small_charging_stations(
            infra_version=self.infra_version,
            start_ocps=self.start_ocps,
            start_year_planning=start_year_planning
        )
        if len(small_charging_projects) > 0:
            self.infra_version.add_projectcontents_to_version_temporary(pc_list=small_charging_projects,
                                                                        update_infra=True)
            for pc in small_charging_projects:
                self.investment_cost += pc.investment_cost
                self.maintenance_cost += pc.maintenance_cost

        for index, sub_area in sub_area_cost.items():
            pc = sub_area["project"]
            self.investment_cost += pc.investment_cost
            self.maintenance_cost += pc.maintenance_cost
            self.project_contents.append(pc)

        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenance_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)

        # the subprojects are already on cost base 2015
        self.cost_2015 = 0
        self.capital_service_cost_2015 = 0
        self.maintenance_cost_2015 = 0
        self.planning_cost_2015 = 0
        self.investment_cost_2015 = 0
        for index, sub_area in sub_area_cost.items():
            pc = sub_area["project"]
            self.investment_cost_2015 = pc.investment_cost
            self.cost_2015 += pc.planned_total_cost
            self.capital_service_cost_2015 += pc.capital_service_cost
            self.maintenance_cost_2015 += pc.maintenance_cost
            self.planning_cost_2015 += pc.planning_cost

        for pc in small_charging_projects:
            self.investment_cost_2015 = pc.investment_cost
            self.cost_2015 += pc.planned_total_cost
            self.capital_service_cost_2015 += pc.capital_service_cost
            self.maintenance_cost_2015 += pc.maintenance_cost
            self.planning_cost_2015 += pc.planning_cost

    def _electrify_complete_infra(self):
        complete_electrification = self.area.calculate_infrastructure_cost(
            traction='electrification',
            infra_version=self.infra_version,
            overwrite=True
        )
        self.infra_version.add_projectcontents_to_version_temporary(
            pc_list=[complete_electrification],
            update_infra=True
        )
        self.area.calc_operating_cost(
            traction='electrification',
            infra_version=self.infra_version,
        )
        try:
            self.cost = self.area.cost_traction('electrification')
        except NoTrainCostError:
            for tg in self.area.traingroups:
                calculation_method = get_calculation_method(traingroup=tg, traction='electrification')
                TimetableTrainCost.create(
                    traingroup = tg,
                    master_scenario_id = self.area.scenario_id,
                    traction = 'electrification',
                    infra_version = self.infra_version,
                    calculation_method = calculation_method
                )
            self.cost = self.area.cost_traction('electrification')

    def _sort_sub_areas_by_usage(self):
        sub_area_by_length = dict()
        for sub_area in self.sub_areas:
            running_km_day = sum([traingroup.running_km_day(self.infra_version.scenario.id) for traingroup in sub_area.traingroups])
            sub_area_by_length[sub_area] = running_km_day
        return sub_area_by_length

    def _calculate_optimisation(self, sub_area_by_length):
        sub_area_cost = dict()

        while sub_area_by_length:
            sub_area = min(sub_area_by_length, key=sub_area_by_length.get)
            sub_area_by_length.pop(sub_area)
            sub_area_cost = self._caluclate_optimization_for_sub_area(
                sub_area=sub_area,
                sub_area_cost=sub_area_cost
            )

        return sub_area_cost

    def _caluclate_optimization_for_sub_area(self, sub_area, sub_area_cost):
        """

        :param sub_area:
        :param sub_area_cost:
        :return:
        """
        """
        Remove the electrification for the sub area and calculate the cost for electrification and for battery
        """
        self.infra_version.remove_electrification_for_rw_lines(rw_lines=sub_area.railway_lines)

        """
        if sgv is in the sub area -> directly calculate cost für electrification
        """
        if 'sgv' in sub_area.categories:
            cost_electrification, pc_electrification = self._calculate_cost_for_sub_area(traction='electrification',
                                                                                         sub_area=sub_area)
            sub_area_cost[sub_area.id] = {
                "preferred_traction": 'electrification',
                "cost_sub_area_electrification": cost_electrification,
                "project": pc_electrification
            }
            return sub_area_cost

        """
        Calculate cost for battery and electrification
        """
        cost_electrification, pc_electrification = self._calculate_cost_for_sub_area(traction='electrification',
                                                                                     sub_area=sub_area)
        cost_battery, pc_battery = self._calculate_cost_for_sub_area(traction='battery', sub_area=sub_area)
        if cost_electrification > cost_battery:
            self.cost = self.cost - cost_electrification + cost_battery
            self.infra_version.add_projectcontents_to_version_temporary(pc_list=[pc_battery], update_infra=True,
                                                                        use_subprojects=True)
            for tg in sub_area.traingroups:
                self.traingroup_to_traction[tg] = "battery"
            preferred_traction = 'battery'
            project = pc_battery
        elif cost_electrification <= cost_battery:
            self.infra_version.add_projectcontents_to_version_temporary(pc_list=[pc_electrification], update_infra=True,
                                                                        use_subprojects=False)
            preferred_traction = 'electrification'
            project = pc_electrification

        sub_area_cost[sub_area.id] = {
            "preferred_traction": preferred_traction,
            "cost_sub_area_battery": cost_battery,
            "cost_sub_area_electrification": cost_electrification,
            "project": project
        }
        return sub_area_cost

    def _calculate_cost_for_sub_area(self, traction, sub_area):
        if traction == 'electrification':
            train_costs = sub_area.calc_operating_cost(
                traction=traction,
                infra_version=self.infra_version,
                traingroup_to_traction=self.traingroup_to_traction
            )
        elif traction == 'battery':
            train_costs = sub_area.calc_operating_cost(
                traction=traction,
                infra_version=self.infra_version,
            )

        base = BaseCalculation()
        cost_traction = 0
        for tc in train_costs:
            cost_year = tc.cost
            cost_base = base.cost_base_year(start_year = parameter.START_YEAR, duration=parameter.DURATION_OPERATION, cost=cost_year, cost_is_sum=False)
            cost_traction += cost_base

        infrastructure_cost = sub_area.calculate_infrastructure_cost(
            traction=traction,
            infra_version=self.infra_version,
            overwrite=True,
            battery_electrify_start_ocps=False
        )
        cost = cost_traction + infrastructure_cost.planned_total_cost
        return cost, infrastructure_cost


class BvwpFillingStation(BvwpCost):
    def __init__(self, start_year_planning, cost_filling_station, infrastructure_type, area, infra_version, kilometer_per_station, abs_nbs='abs'):
        """
        Calculates the cost of a filling station
        :param start_year_planning:
        :param abs_nbs:
        """
        self.maintenance_factor = parameter.MAINTENANCE_FACTOR_FILLING_STATION  # factor from standardisierte Bewertung Tabelle B-19
        self.cost_filling_station = cost_filling_station  # in thousand Euro
        self.infrastructure_type = infrastructure_type
        self.area = area
        self.infra_version = infra_version
        self.kilometer_per_station_h2 = kilometer_per_station

        self.count_stations = self._calculate_count_stations()

        self.investment_cost = self.count_stations * self.cost_filling_station
        self.maintenance_cost = self.investment_cost * self.maintenance_factor
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenance_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)
        super().calc_base_year_cost()

    def _calculate_count_stations(self):
        kilometer_per_stations = self.kilometer_per_station_h2
        length = self.area.length / 1000
        count_stations = math.ceil(length / kilometer_per_stations)
        return count_stations


class BvwpH2InfrastructureCost(BvwpFillingStation):
    def __init__(self, start_year_planning, area, infra_version):
        super().__init__(
            start_year_planning=start_year_planning,
            cost_filling_station = parameter.COST_STATION_H2,
            infrastructure_type = 'filling station h2',
            area = area,
            infra_version=infra_version,
            kilometer_per_station = parameter.KILOMETER_PER_STATION_H2
        )


# class BvwpCostH2(BvwpCost):
#     # TODO: Algorithm for caluclating cost of h2 infrastructure
#     def __init__(self, start_year_planning, railway_lines, abs_nbs='abs'):
#         self.MAINTENANCE_FACTOR_H2 = 0.03
#         self.investment_cost = 1000000000  # TODO: find a algorithm to calculate necessary infrastructure
#         # wasserstofftankstelle wohl 1.000.000 (1 Mio. €)
#         self.maintenace_cost = self.investment_cost * self.MAINTENANCE_FACTOR_H2
#         super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
#                          start_year_planning=start_year_planning, abs_nbs=abs_nbs)


# class BvwpProjectEFuel(BvwpCost):
#     def __init__(self, start_year_planning, abs_nbs='abs'):
#         self.investment_cost = 0
#         self.maintenace_cost = 0
#         super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
#                          start_year_planning=start_year_planning, abs_nbs=abs_nbs)
