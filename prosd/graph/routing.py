import networkx
import logging

from prosd.models import RailwayLine


class GraphRoute:
    def __init__(self, graph, railway_lines_df):
        self.graph = graph
        self.railway_line_df = railway_lines_df  # columns: id, length

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

        route_list = networkx.shortest_path_length(G=self.graph, source=station_source, target=target_sink, weight=self._weight_function_kilometer)

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
            length = self.railway_line_df[self.railway_line_df.railway_line_id == line_id]["railway_line_length"].to_list()[0]

            if length:
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
