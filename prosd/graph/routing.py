import networkx
import logging
import json
import os
import sqlalchemy

from prosd import db
from prosd.models import RouteTraingroup, RailwayStation


class GraphRoute:
    def __init__(self, graph, infra_version):
        self.graph = graph
        self.infra_version = infra_version # columns: id, length

        dirname = os.path.dirname(__file__)
        self.filepath_save_path = os.path.realpath(
            os.path.join(dirname, '../../example_data/railgraph/paths_traingroups/{}.json'))
        self.filepath_save_path_stations = os.path.realpath((
            os.path.join(dirname, '../../example_data/railgraph/paths/{}to{}.json')
        ))

        self.filepath_ignore_ocp = os.path.realpath(os.path.join(dirname, '../../example_data/railgraph/blacklist_route_ignore_ocp.json'))

        with open(self.filepath_ignore_ocp, 'r') as fp:
            self.ignore_ocp_lines = json.load(fp)

    def line(self, traingroup, save_route=True, force_recalculation=False, ignore_ocps=None):
        """

        :return:
        """
        if ignore_ocps is None:
            ignore_ocps = set()
        if force_recalculation:
            old_routes = RouteTraingroup.query.filter(sqlalchemy.and_(RouteTraingroup.traingroup_id == traingroup.id, RouteTraingroup.master_scenario_id == self.infra_version.scenario.id)).all()
            for route in old_routes:
                db.session.delete(route)
            db.session.commit()

        train = traingroup.trains[0]

        ignore_ocps.update(self.ignore_ocp_lines.get(traingroup.id, []))

        # find first ocp
        try:
            first_ocp = train.train_part.first_ocp.ocp.station.db_kuerzel
        except AttributeError:
            logging.warning("TrainGroup " + str(traingroup.id) + " first ocp not existing in railway_station " + str(
                train.train_part.first_ocp.ocp.name) + " " + str(train.train_part.first_ocp.ocp.code))

        # find last ocp
        try:
            last_ocp = train.train_part.last_ocp.ocp.station.db_kuerzel
        except AttributeError:
            logging.warning("TrainGroup " + str(traingroup.id) + " last ocp not existing in railway_station " + str(
                train.train_part.last_ocp.ocp.name) + " " + str(train.train_part.last_ocp.ocp.code))

        # find the via stations (check if they exist)
        via = []
        for tt_ocp in train.train_part.timetable_ocps[1:-1]:
            try:
                if tt_ocp.ocp.code not in ignore_ocps:
                    station = tt_ocp.ocp.station.db_kuerzel
                    via.append(station)
                else:
                    continue
            except AttributeError:
                logging.info("In train_group" + str(traingroup.id) + "tt_ocp " + str(tt_ocp) + " " + str(
                    tt_ocp.ocp.code) + " has no fitting railway_station")
                continue

        # route the traingroup
        try:
            # path = rg.shortest_path_between_stations(graph=graph, station_from=first_ocp, station_to=last_ocp,
            #                                          stations_via=via)
            path = self.route_line(station_from=first_ocp, station_to=last_ocp, stations_via=via, save_route=save_route)
        except networkx.exception.NetworkXNoPath as e:
            logging.error(
                "No path found for traingroup " + str(traingroup.id) + " from " + str(first_ocp) + " to " + str(last_ocp) + " - " + str(e))

        # add to Route Traingroups
        route_traingroups = []
        for index, line_id in enumerate(path["edges"]):
            rtg = RouteTraingroup(
                traingroup_id=traingroup.id,
                railway_line_id=line_id,
                section=index,
                master_scenario_id=self.infra_version.scenario.id
            )
            route_traingroups.append(rtg)

        db.session.add_all(route_traingroups)
        db.session.commit()

        if save_route:
            self._save_path(path, traingroup_id=traingroup.id)

        return route_traingroups

    def route_line(self, station_from, station_to, stations_via, filename=None, save_route=False):
        if len(stations_via) > 0:
            pathes = []
            first_target = str(stations_via[0])
            first_path = self._shortest_path(start_station=station_from, target_station=first_target)
            # first_path = super().shortest_path(graph=graph, source=station_source, target=first_target)
            pathes.extend(first_path)
            for index, station in enumerate(stations_via[:-1]):
                source_from = str(station)
                target_to = str(stations_via[index + 1])
                path = self._shortest_path(start_station=source_from, target_station=target_to)
                # path = super().shortest_path(graph=graph, source=source_from, target=target_to)
                pathes.extend(path)

            last_source = stations_via[-1]
            last_path = self._shortest_path(start_station=last_source, target_station=station_to)
            # last_path = super().shortest_path(graph=graph, source=last_source, target=station_sink)
            pathes.extend(last_path)
            # TODO: Iterate through paths and create one list for nodes and edges
            path = pathes

        else:
            path = self._shortest_path(start_station=station_from, target_station=station_to)
            # lines = self.get_lines_of_path(graph, path)

        lines = self._get_lines_of_path(path)
        station_from_long = RailwayStation.query.filter(
            RailwayStation.db_kuerzel == station_from).scalar()
        station_to_long = RailwayStation.query.filter(RailwayStation.db_kuerzel == station_to).scalar()

        path_dict = {
            "source": station_from,
            "source_id": station_from_long.id,
            "source_name_long": station_from_long.name,
            "sink": station_to,
            "sink_id": station_to_long.id,
            "sink_name_long": station_to_long.name,
            "nodes": path,
            "edges": lines
        }

        if save_route:
            self._save_path_stations(path_dict=path_dict, from_station=station_from, to_station=station_to)

        return path_dict

    def _get_lines_of_path(self, path):
        lines = []
        for index, element in enumerate(path[:-1]):
            if str(element)[-2:] == "in" and str(path[index + 1])[
                                             -3:] == 'out':  # because there are no paths from station_in to station_out if station_in is first element it continues with next combination
                continue
            path_element = (element, path[index + 1])
            edge = self.graph.edges[path_element]
            if isinstance(edge["line"], int):
                line = edge["line"]
                lines.append(line)

        return lines

    def _save_path(self, path_dict, traingroup_id, filename=None):
        if filename is None:
            filepath_save = self.filepath_save_path.format(str(traingroup_id))
        else:
            filepath_save = self.filepath_save_path.format(str(filename))

        path_json = json.dumps(path_dict)
        with open(filepath_save, "w") as f:
            f.write(path_json)

    def _save_path_stations(self, path_dict, from_station, to_station):
        filepath_save = self.filepath_save_path_stations.format(str(from_station),str(to_station))
        path_json = json.dumps(path_dict)
        with open(filepath_save, "w") as f:
            f.write(path_json)

    def reachable_lines(self, start_station, allowed_distance):
        """
        returns all lines that are reachable in an allowed distance from a start_point
        :param allowed_distance: int, in km
        :param start_station:
        :return:
        """
        allowed_distance_m = allowed_distance * 1000

        length_dict = self._shortest_path_length(start_station=start_station, target_station=None)
        length_dict_filtered = {k: v for k, v in length_dict.items() if v < allowed_distance_m and type(k) is int}

        line_ids = list(length_dict_filtered.keys())

        return line_ids

    def _shortest_path_length(self, start_station, target_station):
        """
        calculate the shortest path (length) between the start and the target(s). If target is None, all targets are used
        :param start_station:
        :param target_stations:
        :return:
        """
        station_source = str(start_station) + "_out"

        if target_station is None:
            target_sink = None
        else:
            target_sink = str(target_station) + "_in"

        length = networkx.shortest_path_length(G=self.graph, source=station_source, target=target_sink, weight=self._weight_function_kilometer)

        return length

    def _shortest_path(self, start_station, target_station):
        station_source = str(start_station) + "_out"
        target_sink = str(target_station) + "_in"
        route_list = networkx.shortest_path(G=self.graph, source=station_source, target=target_sink,
                                                   weight=self._weight_function_kilometer_and_electrification)
        return route_list

    def _weight_function_kilometer(self, u, v, d):
        """
        provides a weight function for dijkstra where the weight is the length of the railway_line
        :return:
        """
        MINIMAL_WEIGHT = 0
        weight = MINIMAL_WEIGHT

        edge = d
        if type(edge["line"]) is int:
            line_id = edge["line"]
            length = self.infra_version.get_railwayline_model(line_id).length
            # length = self.railway_line_df[self.railway_line_df.railway_line_id == line_id]["railway_line_model"].to_list()[0].length
            if isinstance(length, int):
                if length > 0:
                    try:
                        weight = int(length)
                    except ValueError:
                        logging.warning(f"{line_id} length in float could not be converted ({length})")
                elif length < 0:
                    logging.warning(f"{line_id} has negativ length ({length})")
                elif length == 0:
                    logging.info(f"{line_id} has 0 length ({length})")
            else:
                logging.warning(f"{line_id} has no length ({length})")
        else:
            weight = MINIMAL_WEIGHT

        return weight

    def _weight_function_kilometer_and_electrification(self, u, v, d):
        """
        provides a weight function for dijkstra where the weight is the length of the railway_line.
        To provide a better algorithm, this weight function prevers railway_lines with catenary a little bit
        :return:
        """
        MINIMAL_WEIGHT = 0
        FACTOR_ELECTRIFICATION = 0.95
        weight = MINIMAL_WEIGHT

        edge = d
        if type(edge["line"]) is int:
            line_id = edge["line"]
            line = self.infra_version.get_railwayline_model(line_id)

            # check if line is closed. If so -> this edge is closed for use.
            if line.closed is True:
                return None

            length = line.length
            if isinstance(length, int):
                if length > 0:
                    try:
                        weight = int(length)
                    except ValueError:
                        logging.info(f"{line_id} length in float could not be converted ({length})")
                elif length < 0:
                    logging.info(f"{line_id} has negativ length ({length})")
                    weight = MINIMAL_WEIGHT
                elif length == 0:
                    logging.info(f"{line_id} has 0 length ({length})")
                    weight = MINIMAL_WEIGHT
            else:
                logging.info(f"{line_id} has no length ({length})")

            catenary = line.catenary

            # TODO: Change that to Stromschiene if s-bahn berlin or hamburg!
            if catenary is True:
                weight = weight * FACTOR_ELECTRIFICATION

        else:
            weight = MINIMAL_WEIGHT

        return weight


