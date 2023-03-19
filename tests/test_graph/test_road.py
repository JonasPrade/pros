from tests.base import BaseTestCase

from prosd.graph.road import RoadDistances

from_ocp = 'AFR'
to_ocp = 'AH'


class TestRoadDistances(BaseTestCase):
    def test_read_road_distances_csv(self):
        rd = RoadDistances()
        rd.read_road_distances_csv()
        self.assertTrue(len(rd.distances)>0)

    def test_get_distance(self):
        rd = RoadDistances()
        distance = rd.get_distance(from_ocp, to_ocp)
        self.assertTrue(distance>0)

    def test_calc_road_distance(self):
        rd = RoadDistances()
        distance = rd.calc_road_distance(from_ocp, to_ocp)
