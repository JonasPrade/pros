import os
import pandas
import logging
import collections
import sqlalchemy
import math
import datetime

from prosd import db
from prosd.models import RailwayLine, RouteTraingroup, VehiclePattern, TimetableOcp, ProjectContent, ProjectGroup, RailwayStation
from prosd.calculation_methods.base import BaseCalculation
from prosd import parameter


class BatteryCapacityError(Exception):
    def __init__(self, message):
        super().__init__(message)


class BvwpCost(BaseCalculation):
    def __init__(self, investment_cost, maintenance_cost, start_year_planning, abs_nbs="abs"):
        # TODO: Change the calculation of that in sepeart funcitons, that is no __init__
        super().__init__()
        self.BASE_YEAR = parameter.BASE_YEAR
        self.p = parameter.RATE
        self.FACTOR_PLANNING = parameter.FACTOR_PLANNING
        self.DURATION_PLANNING = parameter.DURATION_PLANNING
        self.DURATION_OPERATION = parameter.DURATION_OPERATION # because this is only used for electrification
        self.ANUALITY_FACTOR = parameter.ANUALITY_FACTOR

        self.infrastructure_type = None

        self.duration_build = self.duration_building(abs_nbs=abs_nbs)  # TODO That can be rethought
        self.start_year_planning = start_year_planning
        self.start_year_building = self.start_year_planning + self.DURATION_PLANNING
        self.start_year_operation = self.start_year_building + self.duration_build
        self.end_year_operation = self.start_year_operation + self.DURATION_OPERATION

        self.investment_cost = investment_cost
        self.planning_cost = self.investment_cost * self.FACTOR_PLANNING
        self.maintenace_cost = maintenance_cost

        self.planning_cost_2015 = self.cost_base_year(start_year=start_year_planning, duration=self.DURATION_PLANNING,
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
                    cost_factor = self.COST_OVERHEAD_SINGLE_TRACK
                    factor_length = 2
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


class BvwpProjectBattery(BvwpCost):
    def __init__(self, start_year_planning, area, infra_version, abs_nbs='abs'):
        self.infra_version = infra_version
        self.infra_df = infra_version.infra
        self.infrastructure_type = 'battery'
        self.wait_time = datetime.timedelta(minutes=5)  # TODO: find a good wait minute definition
        self.start_year_planning = start_year_planning

        self.project_contents = []
        black_list_train_group = []
        for group in area.traingroups:
            if group in black_list_train_group:
                continue
            else:
                tt_line = group.traingroup_lines
                if tt_line:
                    for tg in tt_line.train_groups:
                        black_list_train_group.append(tg)

                    new_projectcontents = self.calculate_infrastructure(tt_line)
                    self.project_contents.extend(new_projectcontents)
                else:
                    logging.error(f'No line for {group}')

        self.investment_cost = 0
        self.maintenance_cost = 0
        for pc in self.project_contents:
            self.investment_cost += pc.investment_cost
            self.maintenance_cost += pc.maintenance_cost

        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenance_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)

    def calculate_infrastructure(self, tt_line):
        trains = tt_line.get_one_train_cycle(wait_time=self.wait_time)
        station_to_rlml_ocp = self._get_station_to_railml_ocp(trains=trains)

        # calculate the energy need and if there is a problem with the battery capacity
        cycle_sections = self.calc_energy_demand(trains, station_to_rlml_ocp)
        cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta = \
            self._calculate_energy_delta(cycle_sections=cycle_sections, trains=trains)

        """
        if there is a problem with the battery capacity, try to find fitting infrastructure.
        First endpoints get charging stations.
        After that recalculation of the energy demand.
        If still problem with battery capacity -> search for solutions along the line route
        """
        project_contents_temp = []
        if one_cycle_problem or multi_cycle_problem:
            new_projects = self._create_infrastructure_endpoints(cycle_sections, one_cycle_problem, battery_empty,
                                                                  multi_cycle_problem, battery_delta, trains)
            project_contents_temp.extend(new_projects)
            if new_projects:
                self.infra_version.add_projectcontents_to_version_temporary(pc_list=project_contents_temp, update_infra=True)
            cycle_sections = self.calc_energy_demand(trains, station_to_rlml_ocp)
            cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta = \
                self._calculate_energy_delta(cycle_sections=cycle_sections, trains=trains)

        if one_cycle_problem or multi_cycle_problem:
            raise BatteryCapacityError(
                f"After installing loading possibilites at end stations, there is still a battery capacity problem for trainline {tt_line}"
            )
            # TODO: Find ways to electrify belong the cycle, not endpoints

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

        return cycle_sections

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
                timetable = TimetableOcp.query.filter(sqlalchemy.and_(
                    TimetableOcp.train_part == train.train_part.id,
                    TimetableOcp.ocp_id == ocp.id
                )).scalar()
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
        next_train = train.train_group.traingroup_lines.get_next_train(
            previous_train=train,
            list_all_trains=train.train_group.traingroup_lines.all_trains,
            wait_time=self.wait_time
        )
        timetable_train = TimetableOcp.query.filter(sqlalchemy.and_(
            TimetableOcp.train_part == train.train_part.id,
            TimetableOcp.ocp_id == ocp.id
        )).scalar()
        timetable_next_train = TimetableOcp.query.filter(sqlalchemy.and_(
            TimetableOcp.train_part == next_train.train_part.id,
            TimetableOcp.ocp_id == ocp.id
        )).scalar()
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
        order_railway_lines_tuple = db.session.query(RailwayLine.id, RouteTraingroup.section).join(
            RouteTraingroup).filter(
                RouteTraingroup.traingroup_id == tg_id,
                RouteTraingroup.master_scenario_id == self.infra_version.scenario.id
            ).order_by(RouteTraingroup.section).all()
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
                    additional_battery = vehicle_pattern.additional_energy_without_overhead*(train.train_group.length_line_no_catenary(self.infra_version)/train.train_group.length_line(self.infra_version))
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
                            train_group.length_line(self.infra_version) * 1000)))
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
                logging.info(f"OCP {stop} not found in infrastructure database. Calculate this stop manual.")
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
                    proportion_km = (start_km_group + group["length"] / 1000) / length_line(self.infra_version)

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

        if trains[0].train_part.formation.formation_calculation_standi:
            vehicles = trains[0].train_part.formation.formation_calculation_standi.vehicles
        else:
            vehicles = trains[0].train_part.formation.vehicles

        battery_capacity = 0
        for vehicle in vehicles:
            vehicle_pattern = VehiclePattern.query.get(vehicle.vehicle_pattern.vehicle_pattern_id_battery)
            battery_capacity += vehicle_pattern.battery_capacity  # TODO: Add correct battery_capacity to battery vehicle patterns

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
                    battery_empty.append({"cycle_index": index, "section_index": index_section, "battery_status": battery_status})

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
            needed_cycles = len(trains[0].train_group.trains) / trains[0].train_group.traingroup_lines.count_formations
            if possible_cycles < needed_cycles:
                multi_cycle_problem = True
            else:
                multi_cycle_problem = False
        else:
            multi_cycle_problem = False

        return cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta

    def _create_infrastructure_endpoints(self, cycle_sections, one_cycle_problem, battery_empty, multi_cycle_problem,
                               battery_delta, train):
        """

        :param cycle_sections:
        :param one_cycle_problem:
        :param battery_empty:
        :param multi_cycle_problem:
        :param battery_delta:
        :return:
        """
        energy_one_way_problem = False
        energy_cycle_problem = False
        new_project_contents = list()
        PROJECT_GROUP = ProjectGroup.query.get(4)

        new_projects = []
        for segment in cycle_sections:
            last_section = segment[-1]
            ocp_last_section = last_section["last_station"]
            if last_section["catenary"] is False and ocp_last_section["station_charging_point"] is None:
                project_load, possible_charge = self.create_charging_or_catenary_station(
                    station_id=ocp_last_section["station_id"],
                    line=last_section["railway_lines"][-1],
                    duration_stop=ocp_last_section["stop_duration"]
                )
                new_projects.append(project_load)

        return new_projects

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
            logging.error(f"Catenary in {station.name} for {line.id} is too long {line.length}m")

        name = f"Catenary in {station.name} for {line.id}"
        description = f"Oberleitung in {station.name} für die RailwayLine {line.id}"

        infrastructure_cost = BvwpCostElectrification(
            start_year_planning=self.start_year_planning,
            railway_lines_scope=[line],
            infra_version=self.infra_version
        )

        pc = ProjectContent(
            name=name,
            description=description,
            elektrification=True,
            railway_lines=[line],
            investment_cost=infrastructure_cost.investment_cost_2015,
            planning_cost=infrastructure_cost.planning_cost_2015,
            maintenance_cost=infrastructure_cost.maintenance_cost_2015,
            capital_service_cost=infrastructure_cost.capital_service_cost_2015,
            planned_total_cost=infrastructure_cost.cost_2015
        )

        return pc

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

        pc = ProjectContent(
            name=name,
            description=description,
            charging_station=True,
            railway_stations=[station],
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
        self.start_year_planning = start_year_planning
        self.area = area
        self.sub_areas = area.sub_master_areas
        self.infra_version = infra_version

        self.cost = 0

        self.investment_cost = []
        self.maintenance_cost = []

        self._electrify_complete_infra()
        self.traingroup_to_traction = {traingroup: "electrification" for traingroup in self.area.traingroups}
        sub_area_by_length = self._sort_sub_areas_by_usage()
        sub_area_cost = self._calculate_optimisation(sub_area_by_length)

        # TOOD: Calculate investement cost and maintenance cost
        self.investment_cost = 0
        self.maintenance_cost = 0
        self.project_contents = []
        for index, sub_area in sub_area_cost.items():
            pc = sub_area["project"]
            self.investment_cost += pc.investment_cost
            self.maintenance_cost += pc.maintenance_cost
            self.project_contents.append(pc)

        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenance_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)

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
        self.area.calc_train_cost(
            traction='electrification',
            infra_version=self.infra_version,
        )
        self.cost = self.area.cost_traction('electrification')

    def _sort_sub_areas_by_usage(self):
        sub_area_by_length = dict()
        for sub_area in self.sub_areas:
            running_km_day = sum([traingroup.running_km_day(self.infra_version) for traingroup in sub_area.traingroups])
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
        Remove the electrification for the sub area and calculate the cost for electrification and for battery
        """
        self.infra_version.remove_electrification_for_rw_lines(rw_lines=sub_area.railway_lines)
        cost_electrification, pc_electrification = self._calculate_cost_for_sub_area(traction='electrification',
                                                                                     sub_area=sub_area)
        cost_battery, pc_battery = self._calculate_cost_for_sub_area(traction='battery', sub_area=sub_area)

        """
        Compare the calculated cost
        """
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
            train_costs = sub_area.calc_train_cost(
                traction=traction,
                infra_version=self.infra_version,
                traingroup_to_traction=self.traingroup_to_traction
            )
        elif traction == 'battery':
            train_costs = sub_area.calc_train_cost(
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
            overwrite=True
        )
        cost = cost_traction + infrastructure_cost.planned_total_cost
        return cost, infrastructure_cost


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
