import networkx
import itertools
import logging
import math

import sqlalchemy
import geoalchemy2

from prosd.graph.railgraph import RailGraph
from prosd.models import RailwayRoute, RailwayNodes, RailwayLine, RailwayStation
from prosd import db
from tests.base import BaseTestCase


class TestRailGraph(BaseTestCase):
    def setUp(self):
        super().setUp()

        logging.basicConfig(filename='/Users/jonas/PycharmProjects/pros/prosd/log/log_creating_railgraph.log',
                            encoding='utf-8', level=logging.WARNING)

        self.rg = RailGraph()
        self.rg.filepath_save_graphml = '../example_data/railgraph_test/railgraph.pickle'
        self.rg.filepath_save_graph_route = '../example_data/railgraph_test/graphes_routes/{}.pickle'
        self.rg.filepath_save_with_station = '../example_data/railgraph_test/railgraph_with_station.pickle'
        self.rg.filepath_save_with_station_and_parallel_connections = '../example_data/railgraph_test/railgraph_with_station_and_parallel_connections.pickle'

    def test_save_and_load_graph(self):
        # not correct any more
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
            4940,
            4953,
            4951
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
        self.rg.create_graph(use_saved=True)

    def test_add_station_incoming_and_outgoing(self):
        graph = self.rg.load_graph(self.rg.filepath_save_graphml)

        graph_with_station = self.rg.add_station_source_and_sink(graph)

        self.assertIsInstance(graph_with_station, networkx.DiGraph)

    def test_path_beetween_station(self):
        graph = self.rg.load_graph(self.rg.filepath_save_with_station_and_parallel_connections)
        station_from = 'TS'
        station_to = 'BLS'
        path = self.rg.path_between_stations(graph, station_from, station_to)
        self.assertIsInstance(path, list)

    def test_draw_map(self):
        graph = self.rg.load_graph(self.rg.filepath_save_with_station)
        self.rg.draw_map(graph)

    def test_create_connection_parallel_routes_in_station(self):
        graph = self.rg.load_graph(self.rg.filepath_save_with_station)
        graph_with_parallel_connections = self.rg.create_connection_parallel_lines(graph)
        self.rg.save_graph(filepath=self.rg.filepath_save_with_station_and_parallel_connections, graph=graph_with_parallel_connections)

    def test_create_connection_parallel_routes_one_station(self):
        graph = self.rg.load_graph(self.rg.filepath_save_with_station)
        station = RailwayStation.query.get(636)
        graph_new = self.rg.create_connection_parallel_lines_one_station(graph=graph, station=station)

    def test_create_nodes_new_railwaylines(self):
        self.rg.create_nodes_new_railwaylines()

    def test_create_graph_one_route(self):
        # that test covers also;
        # __build_graph_railway_line
        rg = RailGraph()
        route = RailwayRoute.query.filter(RailwayRoute.number == 10007).first()
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

