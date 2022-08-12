import networkx
import itertools
import logging

from prosd.graph.railgraph import RailGraph
from prosd.models import RailwayRoute, RailwayNodes, RailwayLine
from tests.base import BaseTestCase

class TestRailGraph(BaseTestCase):

    def test_save_and_load_graph(self):
        filepath_base = '../example_data/test_save_and_load/{route_number}/{route_number}_{graph_number}.pickle'
        route = RailwayRoute.query.filter(RailwayRoute.number == 4950).one()
        filepath = filepath_base.format(route_number=str(route.number))

        rg = RailGraph()
        graph_list = rg.create_graph_one_route(route=route)
        for index, graph_save in enumerate(graph_list):
            filepath = filepath_base.format(route_number=str(route.number), graph_number=index)
            rg.save_graph(filepath=filepath, graph=graph_save)

        graph_loaded = rg.load_graph(filepath=filepath)
        self.assertIsInstance(graph_loaded, networkx.DiGraph)

    def test_combine_graph_routes(self):
        rg = RailGraph()
        routes = [
            4950,
            4930,
            4953,
            4922,
            4713
        ]
        graph_list = []
        for route_number in routes:
            route = RailwayRoute.query.filter(RailwayRoute.number == route_number).one()
            graph_list_route = rg.create_graph_one_route(route=route)
            for graph in graph_list_route:
                graph_list.append(graph)

        for graph in graph_list:
            rg.railgraph.update(graph)

        # on route 4950
        # end_point = 106953680  # on route 4930
        # end_point = 835403395880  # on route 4953
        start_point = 2432071801
        end_point = 2540221920
        route = networkx.shortest_path(rg.railgraph, start_point, end_point)
        self.assertIsInstance(route, list)

    def test_create_all_graphes(self):
        logging.basicConfig(filename='/Users/jonas/PycharmProjects/pros/prosd/log/log_creating_railgraph.log',
                            encoding='utf-8', level=logging.DEBUG)
        rg = RailGraph()
        rg.create_graph()

    def test_create_graph_one_route(self):
        # that test covers also;
        # __build_graph_railway_line
        rg = RailGraph()
        route = RailwayRoute.query.filter(RailwayRoute.number == 1000).first()
        graph = rg.create_graph_one_route(route=route)
        if graph:
            self.assertIsInstance(graph, networkx.DiGraph)
        else:
            self.assertEqual(
                len(route.railway_lines.all()),
                0
            )

    def test_meter_to_degree(self):
        expected = 1/111000
        input = 1
        rg = RailGraph()
        output = rg._RailGraph__meter_to_degree(input)
        self.assertEqual(expected, output)

    def test_degree_to_meter(self):
        expected = 111000
        input = 1
        rg = RailGraph()
        output = rg._RailGraph__degree_to_meter(input)
        self.assertEqual(expected, output)

    def test_create_id(self):
        reference = [15310, 15210]
        rg = RailGraph()
        output = rg._RailGraph__create_id(reference)
        self.assertIsInstance(output, int)

