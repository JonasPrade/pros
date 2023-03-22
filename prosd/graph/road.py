import pandas
import openrouteservice
from openrouteservice.directions import directions
from prosd.conf import Config
import geoalchemy2
import logging
import os


class CouldNotFoundRoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class RoadDistances:
    def __init__(self):
        dirname = os.path.dirname(__file__)
        self.filepath_road_distances_csv = os.path.realpath(os.path.join(dirname, '../../example_data/railgraph/road_distances.csv'))
        self.distances = self.read_road_distances_csv()

    def read_road_distances_csv(self):
        distances = {}
        df = pandas.read_csv(self.filepath_road_distances_csv, header=0)
        for index, row in df.iterrows():
            distances[row.from_ocp+row.to_ocp] = row.distance_km
            distances[row.to_ocp+row.from_ocp] = row.distance_km  # for both directions

        return distances

    def get_distance(self, from_ocp, to_ocp):
        """
        get the distance in km
        :param from_ocp: str db_kuerzel
        :param to_ocp: str db_kuerzel
        :return:
        """
        key = str(from_ocp+to_ocp)
        if key in self.distances.keys():
            distance = self.distances[key]
        else:
            distance = self.calc_road_distance(
                from_ocp=from_ocp,
                to_ocp=to_ocp
            )
        return distance

    def add_distance_to_csv(self, from_ocp, to_ocp, distance):
        new_row = pandas.DataFrame(
            [[from_ocp, to_ocp, distance]],
            columns=["from_ocp", "to_ocp", "distance_km"]
        )
        df = pandas.read_csv(self.filepath_road_distances_csv, header=0)
        df = pandas.concat([df, new_row])
        df.to_csv(self.filepath_road_distances_csv, index=False)

    def add_distance_to_dict(self, from_ocp, to_ocp, distance):
        self.distances[from_ocp+to_ocp] = distance
        self.distances[to_ocp+from_ocp] = distance

    def calc_road_distance(self, from_ocp, to_ocp):
        from prosd.models import RailwayStation, RailMlOcp

        api_key = Config.API_KEY_OPENROUTESERVICE
        client = openrouteservice.Client(api_key)
        from_station = geoalchemy2.shape.to_shape(RailMlOcp.query.filter(RailMlOcp.code == from_ocp).scalar().station.coordinate_centroid)
        to_station = geoalchemy2.shape.to_shape(RailMlOcp.query.filter(RailMlOcp.code == to_ocp).scalar().station.coordinate_centroid)
        coords = ((from_station.x, from_station.y), (to_station.x, to_station.y))
        try:
            route = directions(client, coords)
        except openrouteservice.exceptions.ApiError:
            raise CouldNotFoundRoadError(
                f"For RailMlOcps {from_ocp} - {to_ocp} no result from openrouteservice because one of the points could not be connected to street. Add that entry manual"
            )

        distance = route["routes"][0]["summary"]["distance"]/1000

        logging.info(f"used openrouteservice to get distance {from_ocp} to {to_ocp} (distance {distance})")

        self.add_distance_to_csv(
            from_ocp=from_ocp,
            to_ocp=to_ocp,
            distance=distance
        )
        self.add_distance_to_dict(
            from_ocp=from_ocp,
            to_ocp=to_ocp,
            distance=distance
        )

        return distance  # in km




