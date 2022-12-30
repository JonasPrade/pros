import os
import pandas
import logging
import collections
import sqlalchemy
import math
import datetime

from prosd import db
from prosd.models import RailwayLine, RouteTraingroup, VehiclePattern, TimetableOcp, TimetableTime, RailwayStation, \
    RailwayPoint, RailwayNodes, RailMlOcp, ProjectContent, ProjectGroup
from prosd.calculation_methods.base import BaseCalculation


class BvwpCost(BaseCalculation):
    def __init__(self, investment_cost, maintenance_cost, start_year_planning, abs_nbs="abs"):
        # TODO: Change the calculation of that in sepeart funcitons, that is no __init__
        super().__init__()
        self.BASE_YEAR = 2015
        self.p = 0.017
        self.FACTOR_PLANNING = 0.18
        self.DURATION_PLANNING = 7
        self.DURATION_OPERATION = 20  # because this is only used for electrification
        self.ANUALITY_FACTOR = 0.0428

        self.duration_build = self.duration_building(abs_nbs=abs_nbs)
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
    def __init__(self, start_year_planning, railway_lines, abs_nbs='abs'):
        self.railway_lines = railway_lines
        self.MAINTENANCE_FACTOR = 0.014  # factor from standardisierte Bewertung Tabelle B-19
        self.COST_OVERHEAD = 588.271  # in thousand Euro

        self.length_no_catenary = self.calc_unelectrified_railway_lines()
        self.cost_overhead = self.length_no_catenary * self.COST_OVERHEAD
        self.cost_substation = 0

        self.investment_cost = self.cost_overhead + self.cost_substation
        self.maintenace_cost = self.investment_cost * self.MAINTENANCE_FACTOR
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)

    def calc_unelectrified_railway_lines(self):
        """
        calculates the length of not electrified lines and returns them. if the line has two tracks, it will multiple the length
        :param railway_lines:
        :return:
        """
        length_no_catenary = 0
        for line in self.railway_lines:
            factor_length = 1
            if line.catenary == False:
                if line.number_tracks == 'zweigleisig':
                    factor_length = 2
                length_no_catenary += line.length * factor_length / 1000

        return length_no_catenary


class BvwpProjectBattery(BvwpCost):
    # TODO: Algorithm for calculating cost of battery infrastructure
    def __init__(self, start_year_planning, rl_id_scope, infra_version, train_groups, abs_nbs='abs'):
        self.infra_version = infra_version
        self.infra_df = infra_version.infra
        self.rl_complete_df = self.infra_df["railway_lines"]

        black_list_train_group = []
        for group in train_groups:
            if group in black_list_train_group:
                continue
            else:
                tt_line = group.traingroup_lines
                if tt_line:
                    for tg in tt_line.train_groups:
                        black_list_train_group.append(tg)

                    self.calculate_energy_line(tt_line)
                else:
                    logging.error(f'No line for {group}')

        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)

    def calculate_energy_line(self, tt_line):
        trains = tt_line.get_one_train_cycle()  # TODO: find a good wait minute definition
        # define a function that calculates the energy need for a train (one direction)
        # therefore the used railway_lines (in order) have to be grouped by their electrification status

        cycle_rw_line_grouped = []
        for train in trains:
            rw_lines_grouped, rw_lines = self._group_railway_lines(train)
            count_stations_to_groups = self._add_count_stations_to_group(line_groups=rw_lines_grouped,
                                                                         rw_lines=rw_lines, train=train)
            rw_lines_grouped = self._calculate_energy(rw_lines_grouped=rw_lines_grouped, train=train,
                                                      count_stations_to_groups=count_stations_to_groups)
            cycle_rw_line_grouped.append(rw_lines_grouped)

        cycle_lines_grouped, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta = \
            self._calculate_energy_delta(cycle_lines_grouped=cycle_rw_line_grouped, trains=trains)

        project_contents_temp = []
        while one_cycle_problem is True or multi_cycle_problem is True:
            db.session.autoflush = False  # needed because otherwise the temporary project_contents get flushed, which fucks up everything
            new_project_content = self._create_infrastructure(cycle_lines_grouped, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta, tt_line=tt_line)
            project_contents_temp = project_contents_temp + new_project_content

            # TODO: following is doubled!
            cycle_rw_line_grouped = []
            for train in trains:

                rw_lines_grouped, rw_lines = self._group_railway_lines(train)
                count_stations_to_groups = self._add_count_stations_to_group(line_groups=rw_lines_grouped,
                                                                             rw_lines=rw_lines, train=train)
                rw_lines_grouped = self._calculate_energy(rw_lines_grouped=rw_lines_grouped, train=train,
                                                          count_stations_to_groups=count_stations_to_groups)
                cycle_rw_line_grouped.append(rw_lines_grouped)

            cycle_lines_grouped, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta = \
                self._calculate_energy_delta(cycle_lines_grouped=cycle_rw_line_grouped, trains=trains)

        if project_contents_temp:
            self.infra_version.add_projectcontents_to_version(pc_list=project_contents_temp, update_infra=False)

        db.session.autoflush = True

    def _group_railway_lines(self, train):
        """
        This function returns a DataFrame of railwaylines - in order of the use by the train - grouped by there attribute "catenary".
        :param train:
        :return:
        """

        def create_new_group(catenary_value, old_group=None):
            if old_group is None:
                group_id = 0
            else:
                group_id = old_group["group_id"] + 1

            group = {
                "group_id": group_id,
                "catenary": catenary_value,
                "length": 0,
                "railway_lines": [],
                "last_station": None,
            }
            return group

        def add_group_to_rw_lines_grouped(group, rw_lines_grouped, last_station):
            group["last_station"] = last_station
            rw_lines_grouped.append(group)
            return rw_lines_grouped

        def add_line_to_group(line, group, group_to_lines):
            group["length"] += line.length / 1000
            group["railway_lines"].append(line)

            # add the group id to the rw_lines
            group_to_lines[line.id] = group["group_id"]
            return group, group_to_lines

        # columns = ["group_id", "catenary", "length", "railway_lines"]
        rw_lines = self._get_rwlines_for_train(train)
        rw_lines_grouped = list()
        group_to_lines = dict()

        catenary_value = rw_lines.iloc[0][1].catenary  # start value of catenary
        group = create_new_group(catenary_value=catenary_value)

        train_stations = train.train_group.stops
        train_stations.remove(train.train_group.first_ocp.ocp)
        train_stations.remove(train.train_group.last_ocp.ocp)
        station_to_rlml_ocp = dict()
        for t_ocp in train_stations:
            if t_ocp.station:
                station_to_rlml_ocp[t_ocp.station] = t_ocp

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
                rw_lines_grouped = add_group_to_rw_lines_grouped(group=group, rw_lines_grouped=rw_lines_grouped, last_station=station_information)
                catenary_value = line.catenary
                group = create_new_group(catenary_value=catenary_value, old_group=group)

            group, group_to_lines = add_line_to_group(line, group, group_to_lines)

        # Add the latest group to the rw_lines_grouped
        station = train.train_group.last_ocp.ocp.station
        station_information = {
            "station_id": station.id,
            "stop_duration": None,
            "station_charging_point": self.infra_df["railway_stations"][
            self.infra_df["railway_stations"].railway_station_id == station.id].railway_station_model.iloc[
            0].charging_station
        }
        rw_lines_grouped = add_group_to_rw_lines_grouped(group=group, rw_lines_grouped=rw_lines_grouped, last_station=station_information)

        # Add the group_id to the railway_lines
        # TODO: That must be m:n
        rw_lines["rw_line_group_id"] = rw_lines["railway_line_id"].map(group_to_lines)
        rw_lines = rw_lines.sort_values(by=["section"])

        # calculate the duration for each rw_lines_grouped
        # TODO: Find a way that orients on the timetable (not an average travel time)
        for segment in rw_lines_grouped:
            segment["duration"] = datetime.timedelta(
                seconds=segment["length"] / train.train_group.travel_speed_average * 3600)

        return rw_lines_grouped, rw_lines

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
            RouteTraingroup.traingroup_id == tg_id).order_by(RouteTraingroup.section).all()
        order_railway_lines = []
        line_to_section = dict()
        for entry in order_railway_lines_tuple:
            line_id = entry[0]
            section = entry[1]
            order_railway_lines.append(line_id)
            line_to_section[line_id] = section

        rw_lines = self.infra_df["railway_lines"][self.infra_df["railway_lines"]["railway_line_id"].isin(order_railway_lines)]
        rw_lines["section"] = rw_lines["railway_line_id"].map(line_to_section)
        rw_lines = rw_lines.sort_values(by=["section"])

        return rw_lines

    def _calculate_energy(self, rw_lines_grouped, train, count_stations_to_groups):
        """
        calculate the needed energy in relation to the battery for a train
        :return:
        """
        # calculate for each rw_lines_ordered the energy needed and battery level
        # TODO: Find a way to implement charging stations
        vehicles = train.train_part.formation.vehicles
        for line_group in rw_lines_grouped:
            energy_sum_group = 0
            energy_running_group = 0
            energy_stops_group = 0
            for vehicle in vehicles:
                vehicle_pattern = VehiclePattern.query.get(vehicle.vehicle_pattern.vehicle_pattern_id_battery)
                length = line_group["length"]
                count_stops = count_stations_to_groups[line_group["group_id"]]

                # calculate the energy used by running for this group
                if line_group["catenary"] == False:
                    additional_battery = vehicle_pattern.additional_energy_without_overhead
                else:
                    additional_battery = 0

                energy_per_km = vehicle_pattern.energy_per_km
                energy_running = (1 + additional_battery) * energy_per_km * length

                # calculate the energy needed for the stops (acceleration etc.)
                energy_stops = self._calc_energy_stops(vehicle_pattern=vehicle_pattern, count_stops=count_stops,
                                                       train_group=train.train_group)

                energy_group = energy_running + energy_stops

                energy_sum_group += energy_group
                energy_running_group += energy_running
                energy_stops_group += energy_stops_group

            line_group["energy"] = energy_sum_group
            line_group["energy_running"] = energy_running_group
            line_group["energy_stops"] = energy_stops_group

        return rw_lines_grouped

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
                intermediate_1 ** 2 - 2 * vehicle_pattern.energy_stop_a * segments * (train_group.length_line * 1000)))
        except ValueError:
            logging.warning(
                f'Could not calculate reference speed for train_group {train_group}. More information on page 197 Verfahrensanleitung Standardisierte Bewertung')
            reference_speed = 160

        energy_per_stop = vehicle_pattern.energy_stop_b * (reference_speed ** 2) * vehicle_pattern.weight * (
                10 ** (-6))
        energy_stops = energy_per_stop * count_stops

        return energy_stops

    def _add_count_stations_to_group(self, line_groups, rw_lines, train):
        """
        calculates the count of stops of a line group
        :return:
        """
        stops = train.train_group.stops
        stops_to_groups = dict()
        length_line = train.train_group.length_line
        travel_time = train.train_group.travel_time
        first_departure = train.train_group.first_ocp.scheduled_time.departure_with_day

        for stop in stops:
            if stop.station:
                lines_of_stations = stop.station.railway_lines
                possible_groups = set(
                    rw_lines[rw_lines["railway_line_model"].isin(lines_of_stations)]["rw_line_group_id"].to_list())
                if len(possible_groups) > 1:
                    # there is more than one group possible
                    # check if only one has catenary
                    group_list = list()
                    for group in line_groups:
                        group_id = group["group_id"]
                        if group_id in possible_groups and group["catenary"] == True:
                            group_list.append(group_id)

                    group_list = sorted(group_list)

                    if len(group_list) >= 1:
                        stops_to_groups[stop.id] = group_list[0]

                elif len(possible_groups) == 1:
                    stops_to_groups[stop.id] = possible_groups.pop()
                else:
                    logging.error(f"Possible Groups has a non valid length {possible_groups}")
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
                    proportion_km = (start_km_group + group["length"] / 1000) / length_line

                    if travel_time_proportion > proportion_km:
                        start_km_group += group["length"] / 1000
                        continue
                    else:
                        stops_to_groups[stop.id] = group["group_id"]
                        break

        count_stations_groups = collections.Counter(stops_to_groups.values())
        return count_stations_groups

    def _calculate_energy_delta(self, cycle_lines_grouped, trains):
        """
        calculates the input and output of energy for the line groups.
        :param rw_lines_grouped:
        :param train:
        :return:
        """
        CHARGE = 1200  # TODO: Find value of added kW.

        vehicles = trains[0].train_part.formation.vehicles
        battery_capacity = 0
        for vehicle in vehicles:
            vehicle_pattern = VehiclePattern.query.get(vehicle.vehicle_pattern.vehicle_pattern_id_battery)
            battery_capacity += vehicle_pattern.battery_capacity  # TODO: Add correct battery_capacity to battery vehicle patterns

        battery_status = battery_capacity
        battery_empty = []
        for index, segment in enumerate(cycle_lines_grouped):
            train = trains[index]
            arrival_last_ocp = train.train_part.last_ocp.scheduled_time.arrival_with_day

            for index_line_group, line_group in enumerate(segment):
                if line_group["catenary"] == True:
                    duration = line_group["duration"]
                    charge = CHARGE * (
                                duration.seconds / 3600) + battery_status
                    battery_status = min(battery_capacity, charge)
                else:
                    battery_status = battery_status - line_group["energy"]
                    line_group["battery_after_group"] = battery_status

                    # add energy to battery if there is a charging station
                    if line_group["last_station"]:
                        if line_group["last_station"]["station_charging_point"] is True and index_line_group != len(segment) - 1:
                            # the last segment has to be calculated the duration of standing first before there can be added a charge
                            charge = CHARGE * (line_group["last_station"]["stop_duration"].seconds/3600) + battery_status
                            battery_status = min(battery_status, charge)
                    
                    if battery_status < 0:
                        battery_empty.append([index, index_line_group])

            # add the time that the vehicle stands at the end of a segment
            if index != len(
                    cycle_lines_grouped) - 1:  # so in this case, there is a following segment of the train cycle
                departure_next_segment = trains[index + 1].train_part.first_ocp.scheduled_time.departure_with_day
            else:
                departure_next_segment = trains[1].train_part.first_ocp.scheduled_time.departure_with_day

            stand_time = departure_next_segment - arrival_last_ocp

            if segment[-1]["catenary"] is True or segment[-1]["last_station"]["station_charging_point"] is True:  # this is the latest line_group of the segment
                charge = CHARGE * (stand_time.seconds / 3600) + battery_status
                battery_status = min(battery_capacity, charge)
                # TODO: Add that to information to the cycle_lines_grouped

        # check if the energy is enough for on cycle
        if len(battery_empty) > 0:
            one_cycle_problem = True
        else:
            one_cycle_problem= False

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

        return cycle_lines_grouped, one_cycle_problem, battery_empty, multi_cycle_problem, battery_delta

    def _create_infrastructure(self, cycle_lines_grouped, one_cycle_problem, battery_empty, multi_cycle_problem,
                               battery_delta, tt_line):
        """

        :param cycle_lines_grouped:
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

        # TODO: Check if both ocp (first and last) can charge (or is electrified)
        if cycle_lines_grouped[0][0]["catenary"] or tt_line.train_groups[0].first_ocp.ocp.station.charging_station:
            first_ocp_electrified = True
        else:
            first_ocp_electrified = False

        if cycle_lines_grouped[-1][0]["catenary"] or tt_line.train_groups[0].last_ocp.ocp.station.charging_station:
            last_ocp_electrified = True
        else:
            last_ocp_electrified = False

        if first_ocp_electrified is True and last_ocp_electrified is True:
            both_ocp_electrified = True
        else:
            both_ocp_electrified = False

        # analyse where some infrastructure is needed
        if one_cycle_problem:
            for record in battery_empty:
                if record[0] == 0:
                    energy_one_way_problem = True
                if record[0] == 1:
                    energy_cycle_problem = True

        # if the energy is empty in the first segment -> some charging or electrification at the line
        if energy_one_way_problem:
            logging.error(f"There is an energy_one_way_problem for {tt_line}, but there are no solutions for that yet")
            #TODO: Check if there is a longer stop to charge
            #TODO: if not -> electrify a railway sector
            pass

        # if the energy gets empty at the second segment -> try recharging at the turning stations
        elif energy_cycle_problem:
            if both_ocp_electrified is False:
                if last_ocp_electrified is False:
                    pc_charge_last_ocp_temp = self.create_charging_project_content(
                        station=tt_line.train_groups[0].last_ocp.ocp.station,
                        project_group=[PROJECT_GROUP]
                    )
                    new_project_contents.append(pc_charge_last_ocp_temp)
                    logging.info(f"Added {pc_charge_last_ocp_temp} at station {pc_charge_last_ocp_temp.railway_stations}")
                elif first_ocp_electrified is False:
                    pc_charge_first_ocp_temp = self.create_charging_project_content(
                        station=tt_line.train_groups[0].first_ocp.ocp.station,
                        project_group=[PROJECT_GROUP]
                    )
                    new_project_contents.append(pc_charge_first_ocp_temp)
                    logging.info(
                        f"Added {pc_charge_first_ocp_temp} at station {pc_charge_first_ocp_temp.railway_stations}")
            else:
                # TODO: Try to add a charging station at other point
                pass

            # TODO: if not -> electrify a railway_sector
            pass

        elif multi_cycle_problem:
            # TODO: Add multi_cycle_problem
            pass

        # add the new created (but not commited) project_contents
        for pc in new_project_contents:
            self.infra_version.load_single_project_to_version(pc)

        return new_project_contents

    def create_charging_project_content(self, station, project_group):
        """
        Create a project_content with a charging point at a specific station
        :return:
        """
        # TODO: Have in mind to ggf. create project to create hierarchy
        name = f"Ladestation {station.name}"
        description=f"Erstelle Ladestation in {station.name}"

        pc = ProjectContent(
            name=name,
            description=description,
            charging_station=True,
            projectcontent_groups=project_group,
            effects_passenger_local_rail=True,
            railway_stations=[station]
        )

        # TODO: Add Cost calculation!
        # TODO: ProjectContent Number

        # the pc is not added to the database yet, because it use case has still to be proven.

        return pc

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
