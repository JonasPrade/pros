import networkx
import shapely
import logging
import uuid
import sqlalchemy
import os
import json
import geoalchemy2
import math
import itertools
import time

from prosd import models, db
from prosd.graph.graph import GraphBasic


class PointOfLineNotAtEndError(Exception):
    def __init__(self, message):
        super().__init__(message)


class SubnodeHasNoNodeID(Exception):
    def __init__(self, message):
        super().__init__(message)


class RailGraph(GraphBasic):
    def __init__(self):
        self.railgraph = networkx.DiGraph()

        dirname = os.path.dirname(__file__)

        self.filepath_save_graphml = os.path.realpath(
            os.path.join(dirname, '../../example_data/railgraph/railgraph.pickle'))
        self.filepath_save_graph_route = os.path.realpath(
            os.path.join(dirname, '../../example_data/railgraph/graphes_routes/{}.pickle'))

        filepath_whitelist_parallel_routes = os.path.realpath(
            os.path.join(dirname, '../../example_data/railgraph/whitelist_parallel_routes.json'))
        with open(filepath_whitelist_parallel_routes) as json_file:
            self.whitelist_parallel_routes = json.load(json_file)

        filepath_whitelist_ignore_route_graph = os.path.realpath(os.path.join(dirname,
                                                                              '../../example_data/railgraph/whitelist_ignore_route_graph.json'))
        with open(filepath_whitelist_ignore_route_graph) as json_file:
            self.whitelist_ignore_route_graph = json.load(json_file)

        filepath_whitelist_endpoints = os.path.realpath(os.path.join(dirname,
                                                                     '../../example_data/railgraph/whitelist_endpoints.json'))
        with open(filepath_whitelist_endpoints) as json_file:
            self.whitelist_endpoints = json.load(json_file)

        self.filepath_save_with_station = os.path.realpath(
            os.path.join(dirname, '../../example_data/railgraph/railgraph_with_station.pickle'))
        self.filepath_save_with_station_and_parallel_connections = os.path.realpath(os.path.join(dirname,
                                                                                                 '../../example_data/railgraph/railgraph_with_station_and_parallel_connections.pickle'))
        self.filepath_save_path = os.path.realpath(
            os.path.join(dirname, '../../example_data/railgraph/paths/{}.json'))

        self.angle_allowed_min = 60
        self.angle_allowed_max = 360 - self.angle_allowed_min

        self.ALLOWED_DISTANCE_IN_NODE = self.__meter_to_degree(
            1)  # allowed distance between that are assumed to be on node [m]

    def create_graph(self, new_nodes=False, use_saved_route=True):
        """
        Imports the RailwayLines of the db and creates a manipulate_geodata_and_db out of the data
        :return:
        """
        # Import RailwayLines

        # railway_lines = views.RailwayLinesSchema(many=True).dump(models.RailwayLine.query.all())
        railway_lines = models.RailwayLine.query.all()

        if new_nodes:
            self.create_nodes(railway_lines, overwrite=True)
        else:
            self.create_nodes_new_railwaylines()

        # create graphes of each route
        graph_list = self._create_graphes_routes(use_saved=use_saved_route)

        # connect graphes to one manipulate_geodata_and_db
        for graph in graph_list:
            self.railgraph.update(graph)

        self.save_graph(self.filepath_save_graphml, graph=self.railgraph)

        graph_with_station = self.add_station_source_and_sink(graph=self.railgraph)
        self.save_graph(self.filepath_save_with_station, graph=graph_with_station)
        self.railgraph = graph_with_station

        graph_with_station_and_connection_in_station = self.create_connection_parallel_lines(graph=self.railgraph)
        self.save_graph(self.filepath_save_with_station_and_parallel_connections, graph=self.railgraph)
        self.railgraph = graph_with_station_and_connection_in_station

        return

    def save_graph(self, filepath, graph):
        """
        saves a manipulate_geodata_and_db
        :param filepath:
        :param graph: a list of graphes or a manipulate_geodata_and_db itself
        :return:
        """

        networkx.write_gpickle(path=filepath, G=graph)

    def load_graph(self, filepath):
        """
        loads a manipulate_geodata_and_db
        :param filepath:
        :return:
        """
        G = networkx.read_gpickle(path=filepath)
        return G

    def delete_graph_route(self, route_number):
        filepath = self.filepath_save_graph_route.format(str(route_number))
        if os.path.exists(filepath):
            os.remove(filepath)

    def create_nodes_new_railwaylines(self):
        """
        get all railway_lines tahat have no start_node or end_node. Check if a node already exists at that coordiante
        if not, create a new node
        :return:
        """
        # get all railway_lines, that have no start_node or no end_node
        # check if a node already exists at that coordinate
        # if not, create a new node
        RailwayLine = models.RailwayLine

        new_lines = db.session.query(RailwayLine).filter(
            sqlalchemy.or_(RailwayLine.start_node == None, RailwayLine.end_node == None)
        ).all()

        for line in new_lines:
            wkb = shapely.wkb.loads(line.coordinates.desc, hex=True)
            start_coord, end_coord = wkb.boundary
            start_coord = shapely.wkb.dumps(start_coord, hex=True, srid=4326)
            end_coord = shapely.wkb.dumps(end_coord, hex=True, srid=4326)

            if not line.start_node:
                node_id = models.RailwayNodes.add_node_if_not_exists(coordinate=start_coord).id
                db.session.query(RailwayLine).filter(RailwayLine.id == line.id).update(dict(start_node=node_id),
                                                                                       synchronize_session=False)
                db.session.commit()

            if not line.end_node:
                node_id = models.RailwayNodes.add_node_if_not_exists(coordinate=end_coord).id
                db.session.query(RailwayLine).filter(RailwayLine.id == line.id).update(dict(end_node=node_id),
                                                                                       synchronize_session=False)
                db.session.commit()

    def combine_nodes(self, node1_id, node2_id):
        """
        combines two nodes and connects all edges of both nodes to one node. The other node gets deleted.
        :param node2_id:
        :param node1_id:
        :return:
        """
        RailwayLine = models.RailwayLine
        Nodes = models.RailwayNodes

        # get all lines that are connected to node2
        lines_start_node2 = db.session.query(RailwayLine).filter(
            RailwayLine.start_node == node2_id
        ).update(dict(
            start_node=node1_id
        ))
        lines_end_node2 = db.session.query(RailwayLine).filter(
            RailwayLine.end_node == node2_id
        ).update(dict(
            end_node=node1_id
        ))

        db.session.query(Nodes).filter(Nodes.id == node2_id).delete()
        db.session.commit()

    def create_nodes(self, railway_lines, overwrite=True):
        """
        Creates nodes based on a railway_lines (geodata)
        :param railway_lines:
        :param overwrite: Boolean, if True it deletes all existing nodes
        :return:
        """
        Nodes = models.RailwayNodes
        if overwrite:
            db.session.query(Nodes).delete()
            db.session.commit()

        coord_dict = dict()  # list that collects all coords, so it can be controlled if a node already exists
        ids = []
        lines_to_nodes = dict()  # railway_line.id to (railway_nodes.id, railway_nodes.id) (start_node, end_node)
        db_commits = []

        for line in railway_lines:
            wkb = shapely.wkb.loads(line.coordinates.desc, hex=True)
            start_coord, end_coord = wkb.boundary
            start_coord = shapely.wkb.dumps(start_coord, hex=True, srid=4326)
            end_coord = shapely.wkb.dumps(end_coord, hex=True, srid=4326)

            # check if a start_node already exists in nodes_db. If yes, this will be used. In other case, a node will be created

            start_node, coord_dict, db_commits = self._check_nodes_exists(coord=start_coord, nodes_list=coord_dict,
                                                                          Model=Nodes, commit_list=db_commits,
                                                                          idlist=ids)

            end_node, coord_dict, db_commits = self._check_nodes_exists(coord=end_coord, nodes_list=coord_dict,
                                                                        Model=Nodes, commit_list=db_commits,
                                                                        idlist=ids)

            lines_to_nodes[line.id] = (start_node.id, end_node.id)

        db.session.add_all(db_commits)
        db.session.commit()

        for line_id, nodes in lines_to_nodes.items():
            db.session.query(models.RailwayLine).filter(models.RailwayLine.id == line_id).update(
                dict(start_node=nodes[0], end_node=nodes[1]),
                synchronize_session=False
            )

        db.session.commit()
        logging.info('Creation of all nodes finished')

    def _create_graphes_routes(self, use_saved=True):
        """
        create graphes for all routes
        :return:
        """
        # Get all Routes
        railway_routes = models.RailwayRoute.query.all()

        # Iterate trough Routes
        graph_list = []
        for route in railway_routes:
            filepath_graph_route = self.filepath_save_graph_route.format(str(route.number))
            if os.path.exists(filepath_graph_route) and use_saved:
                graph = self.load_graph(filepath_graph_route)
                if graph:
                    graph_list.append(graph)
            else:
                try:
                    st = time.time()
                    graph = self.create_graph_one_route(route)
                    if graph:
                        graph_list.append(graph)
                    et = time.time()
                    run_time = et - st
                    logging.debug("RunTime route " + str(route.number) + " " + str(run_time))
                except Exception as e:
                    logging.error("Error at route " + str(route.number) + " " + str(route.name) + " " + str(e))

        return graph_list

    def create_graph_one_route(self, route, save=True):
        """
        creates a manipulate_geodata_and_db for one route
        :return:
        """
        lines = route.railway_lines

        if len(lines.all()) == 0:
            logging.info("No railwaylines for route: " + str(route.number) + " " + str(route.name))
            return
        elif str(route.number) in self.whitelist_ignore_route_graph:
            logging.info("Route " + str(route.number) + " " + str(route.name) + " is ignored")
            return
        else:
            # first check, if all stations have a node. If not, new nodes are created and lines are splitted
            self._check_all_stations_have_nodes(route=route)
            db.session.refresh(route)

            self._check_end_nodes_other_lines(route=route)
            db.session.refresh(route)

            G, remaining_lines = self._build_graph_railway_line(lines, route)

            # There is a possibility, that not all railway lines have been used. Either because of parallel route or
            # an interrupted route
            if len(remaining_lines.all()) > 0:
                if str(route.number) in self.whitelist_parallel_routes:
                    while remaining_lines.all():
                        new_graph, remaining_lines = self._build_graph_railway_line(lines=remaining_lines, route=route)
                        G.update(new_graph)
                else:
                    logging.warning("For route " + str(route.number) + " " + str(
                        route.name) + " there are RailwayLines that are not part of Graph. RailwayLines are" + str(
                        remaining_lines.all()))

            if save:
                self.save_graph(graph=G, filepath=self.filepath_save_graph_route.format(str(route.number)))

            return G

    def add_station_source_and_sink(self, graph):
        """
        adds for all stations the source and sink for easier routing
        :return:
        """
        stations = models.RailwayStation.query.all()

        for station in stations:
            time_start = time.time()
            # get the station db_kuerzel
            station_sink_node = str(station.db_kuerzel) + "_in"
            station_source_node = str(station.db_kuerzel) + "_out"

            node_data = {"node_id": station.id}
            graph = self.add_node_to_graph(graph=graph, node_name=station_sink_node, node_data=node_data)
            graph = self.add_node_to_graph(graph=graph, node_name=station_source_node, node_data=node_data)
            # manipulate_geodata_and_db.add_node(station_sink_node)
            # manipulate_geodata_and_db.add_node(station_source_node)

            nodes = station.railway_nodes
            # iterate through nodes and establish connections from each input of a node to the station_in
            # and from the station_out to each output of a node
            for node in nodes:
                lines_of_node = node.lines
                for line in lines_of_node:
                    # incoming
                    line_incoming_node = self._create_subnode_id(node_id=node.id, line_id=line.id, direction=0)
                    graph = self.add_node_to_graph(graph=graph, node_name=line_incoming_node,
                                                   node_data={"node_id": node.id})
                    graph = self.add_edge(graph, line_incoming_node, station_sink_node,
                                          edge_data={"line": "station_line_sink"})

                    # outgoing
                    line_outgoing_node = self._create_subnode_id(node_id=node.id, line_id=line.id, direction=1)
                    graph = self.add_node_to_graph(graph=graph, node_name=line_outgoing_node,
                                                   node_data={"node_id": node.id})
                    graph = self.add_edge(graph, station_source_node, line_outgoing_node,
                                          edge_data={"line": "station_line_source"})

            time_end = time.time()
            logging.info(f"Needed time for {station}: {time_end-time_start}")
        return graph

    def create_connection_parallel_lines(self, graph):
        """
        some lines are parallel in stations and are not connect. So allow them to connect, if the station is a "Bahnhof".
        :return:
        """
        stations = models.RailwayStation.query.filter(models.RailwayStation.type == "Bf").all()

        for station in stations:
            graph = self.create_connection_parallel_lines_one_station(station=station, graph=graph)
        return graph

    def create_connection_parallel_lines_one_station(self, station, graph):
        """

        :param station:
        :param graph:
        :return:
        """
        nodes = station.railway_nodes

        if len(nodes) > 1:
            node_ids = []
            for node in nodes:
                node_ids.append(node.id)

            graph_nodes = []
            for n in graph.nodes(data=True):
                try:
                    if n[1]["node_id"] in node_ids:
                        graph_nodes.append(n[0])
                except KeyError:
                    logging.info("node " + str(n) + " has no <node_id>")

            # graph_nodes = [n for n, v in manipulate_geodata_and_db.nodes(data=True) if v["node_id"] in node_ids]
            graph_station = graph.subgraph(graph_nodes)

            for node in nodes:
                lines = node.lines
                for line in lines:
                    outgoing_line = self._create_subnode_id(node_id=node.id, line_id=line.id, direction=1)
                    lines_other_nodes = set(station.railway_lines) - set(node.lines)

                    for line_other_node in lines_other_nodes:
                        node_of_other_line = list(set(node_ids) & set(line_other_node.nodes))[0]
                        ingoing_line = self._create_subnode_id(node_id=node_of_other_line,
                                                               line_id=line_other_node.id, direction=0)
                        path_exists = self.check_path_exists(graph_station, outgoing_line, ingoing_line)
                        if not path_exists:
                            # Check if the angle allows a path. Because they have no same node, get_angle_two_lines does not work
                            line_outgoing_node = node
                            line_outgoing_next_point = models.RailwayLine.get_next_point_of_line(line=line,
                                                                                                 point=line_outgoing_node.coordinate)
                            line_ingoing_node = models.RailwayNodes.query.get(node_of_other_line)
                            line_ingoing_next_point = models.RailwayLine.get_next_point_of_line(line=line_other_node,
                                                                                                point=line_ingoing_node.coordinate)
                            angle_rad = db.session.execute(sqlalchemy.select(
                                geoalchemy2.func.ST_Angle(line_outgoing_node.coordinate, line_outgoing_next_point,
                                                          line_ingoing_node.coordinate, line_ingoing_next_point)
                            )).scalar()
                            angle_degree = math.degrees(angle_rad)

                            if self.angle_allowed_min < angle_degree < self.angle_allowed_max:
                                self.add_edge(graph=graph, node1=outgoing_line, node2=ingoing_line,
                                              edge_data={"line": "inside_node_line"})

        return graph

    def _create_turner(self, G, node, connect_same_route=False, allow_turn_on_same_line=False):
        """
        in some nodes not all combination of edges are allowed. This function creates a sub-node where only that combination are allowed that are possibly to use.
        For that generally:

        :return:
        """
        if node.point:
            if node.point[0].type == 'Bf':
                allow_turn_on_same_line = True

        G = self.__build_directed_graph_with_subnodes(G=G, node=node)
        G = self.__find_and_connect_allowed_connections(G=G, node=node, connect_same_route=connect_same_route,
                                                        allow_turn_on_same_line=allow_turn_on_same_line)

        return G

    def _check_end_nodes_other_lines(self, route):
        """
        # check, if there are ending-nodes of other lines that are on that line and the line has no node at that point. In this case split the lines there
        :return:
        """
        nodes = models.RailwayRoute.get_nodes_whose_endpoints_on_input_route(input_route=route)
        for node in nodes:
            if len(node.routes_number) > 0:
                old_line = models.RailwayPoint.get_line_of_route_that_intersects_point(coordinate=node.coordinate,
                                                                                       route_number=route.number)
                models.RailwayLine.split_railwayline(old_line_id=old_line.id, blade_point=node.coordinate)

    def _remove_line_from_graph(self, G, line):
        """

        :param G: manipulate_geodata_and_db networkx
        :param line: a line (from model RailwayLine)
        :return:
        """
        start_node_out = self._create_subnode_id(node_id=line.start_node, line_id=line.id, direction=1)
        start_node_in = self._create_subnode_id(node_id=line.start_node, line_id=line.id, direction=0)
        end_node_in = self._create_subnode_id(node_id=line.end_node, line_id=line.id, direction=0)
        end_node_out = self._create_subnode_id(node_id=line.end_node, line_id=line.id, direction=1)

        G.remove_edge(start_node_out, end_node_in)
        G.remove_edge(end_node_out, start_node_in)

        return G

    def _add_line_to_graph(self, graph, line):
        """
        adds a line to an existing manipulate_geodata_and_db
        :param G:
        :param line:
        :return:
        """
        # add the edges
        start_node_out = self._create_subnode_id(node_id=line.start_node, line_id=line.id, direction=1)
        start_node_in = self._create_subnode_id(node_id=line.start_node, line_id=line.id, direction=0)
        end_node_in = self._create_subnode_id(node_id=line.end_node, line_id=line.id, direction=0)
        end_node_out = self._create_subnode_id(node_id=line.end_node, line_id=line.id, direction=1)

        graph = self.add_node_to_graph(graph=graph, node_name=start_node_out, node_data={"node_id": line.start_node})
        graph = self.add_node_to_graph(graph=graph, node_name=start_node_in, node_data={"node_id": line.start_node})
        graph = self.add_node_to_graph(graph=graph, node_name=end_node_in, node_data={"node_id": line.end_node})
        graph = self.add_node_to_graph(graph=graph, node_name=end_node_out, node_data={"node_id": line.end_node})

        graph = self.add_edge(graph=graph, node1=start_node_out, node2=end_node_in, edge_data={"line": line.id})
        graph = self.add_edge(graph=graph, node1=end_node_out, node2=start_node_in, edge_data={"line": line.id})
        # G.add_edge(start_node_out, end_node_in)
        # G.add_edge(end_node_out, start_node_in)

        # recalculate the turner
        start_node = models.RailwayNodes.query.get(line.start_node)
        end_node = models.RailwayNodes.query.get(line.end_node)

        graph = self.__find_and_connect_allowed_connections(G=graph, node=start_node)
        graph = self.__find_and_connect_allowed_connections(G=graph, node=end_node)

        return graph

    def __build_directed_graph_with_subnodes(self, G, node):
        """
        
        :param node: 
        :return: 
        """
        ## correct the Graph for the node.
        lines = node.lines
        # Adds new edges that point to an own subnode and remove the old edges
        incoming_edges = list(G.in_edges(node.id))

        for u, v in incoming_edges:
            line = models.RailwayLine.query.filter(models.RailwayLine.id == G.get_edge_data(u, v)["line"]).one()
            node_u_id = models.RailwayLine.get_other_node_of_line(line, node.id).id
            subnode_u_id = self._create_subnode_id(node_id=node_u_id, line_id=line.id, direction=1)
            subnode_v_id = self._create_subnode_id(node_id=node.id, line_id=line.id, direction=0)
            G = self.add_node_to_graph(graph=G, node_name=subnode_u_id, node_data={"node_id": node_u_id})
            G = self.add_node_to_graph(graph=G, node_name=subnode_v_id, node_data={"node_id": node.id})
            G = self.add_edge(graph=G, node1=subnode_u_id, node2=subnode_v_id, edge_data={"line": line.id})

        G.remove_edges_from(incoming_edges)

        outgoing_edges = list(G.edges(node.id))
        for u, v in outgoing_edges:
            line = models.RailwayLine.query.filter(models.RailwayLine.id == G.get_edge_data(u, v)["line"]).one()
            node_v_id = models.RailwayLine.get_other_node_of_line(line, node.id).id
            subnode_u_id = self._create_subnode_id(node_id=node.id, line_id=line.id, direction=1)
            subnode_v_id = self._create_subnode_id(node_id=node_v_id, line_id=line.id, direction=0)
            G = self.add_node_to_graph(graph=G, node_name=subnode_u_id, node_data={"node_id": node.id})
            G = self.add_node_to_graph(graph=G, node_name=subnode_v_id, node_data={"node_id": node_v_id})
            G = self.add_edge(graph=G, node1=subnode_u_id, node2=subnode_v_id, edge_data={"line": line.id})

        G.remove_edges_from(outgoing_edges)
        G.remove_node(node.id)

        return G

    def __find_and_connect_allowed_connections(self, G, node, connect_same_route=False, allow_turn_on_same_line=False):
        """

        :param G:
        :param lines:
        :return:
        """
        lines = node.lines

        allowed_connections = list()
        for in_line in lines:
            for out_line in lines:
                if in_line.id == out_line.id:
                    if allow_turn_on_same_line:
                        G, allowed_connections = self.__connect_lines_turner(G=G, node=node, line1=in_line,
                                                                             line2=out_line,
                                                                             allowed_connections=allowed_connections)
                    continue
                elif in_line.route_number == out_line.route_number and connect_same_route:
                    G, allowed_connections = self.__connect_lines_turner(G=G, node=node, line1=in_line,
                                                                         line2=out_line,
                                                                         allowed_connections=allowed_connections)
                else:
                    angle_check = models.RailwayLine.get_angle_two_lines(line1=in_line, line2=out_line, node=node)
                    if angle_check:
                        G, allowed_connections = self.__connect_lines_turner(G=G, node=node, line1=in_line,
                                                                             line2=out_line,
                                                                             allowed_connections=allowed_connections)
        return G

    def __connect_lines_turner(self, G, node, line1, line2, allowed_connections):
        if not [line1, line2] in allowed_connections:
            subnode_1_in = self._create_subnode_id(node_id=node.id, line_id=line1.id, direction=0)
            subnode_1_out = self._create_subnode_id(node_id=node.id, line_id=line1.id, direction=1)
            subnode_2_in = self._create_subnode_id(node_id=node.id, line_id=line2.id, direction=0)
            subnode_2_out = self._create_subnode_id(node_id=node.id, line_id=line2.id, direction=1)

            G = self.add_node_to_graph(graph=G, node_name=subnode_1_in,
                                       node_data={"node_id": node.id})
            G = self.add_node_to_graph(graph=G, node_name=subnode_1_out,
                                       node_data={"node_id": node.id})
            G = self.add_node_to_graph(graph=G, node_name=subnode_2_in, node_data={"node_id": node.id})
            G = self.add_node_to_graph(graph=G, node_name=subnode_2_out, node_data={"node_id": node.id})

            G = self.add_edge(graph=G, node1=subnode_1_in, node2=subnode_2_out, edge_data={"line": "inside_node_line"})
            G = self.add_edge(graph=G, node1=subnode_2_in, node2=subnode_1_out,
                              edge_data={"line": "inside_node_line"})

            # G.add_edge(subnode_1_in, subnode_2_out)
            # G.add_edge(subnode_2_in, subnode_1_out)
            allowed_connections.append([line1, line2])
        return G, allowed_connections

    def _create_subnode_id(self, node_id, line_id, direction):
        """

        :param node_id: int id of node
        :param line_id: int id of line
        :param direction: int 0 or 1
        :return:
        """
        subnode_id = int(str(node_id) + str(line_id) + str(direction))
        return subnode_id

    def _build_graph_railway_line(self, lines, route):
        """

        :return:
        """
        Line = models.RailwayLine
        G = networkx.DiGraph()
        open_nodes = set()
        end_nodes = set()
        added_lines = set()

        first_line = lines[0]

        # add two edges (each direction)
        G = self.__add_edges_both_directions(graph=G, node1=first_line.start_node, node2=first_line.end_node,
                                             line=first_line)
        # G.add_edge(first_line.start_node, first_line.end_node, line=first_line.id)
        # G.add_edge(first_line.end_node, first_line.start_node, line=first_line.id)

        open_nodes.add(first_line.start_node)
        open_nodes.add(first_line.end_node)
        added_lines.add(first_line.id)

        # create the manipulate_geodata_and_db
        if len(lines.all()) > 1:
            while open_nodes:
                node = list(open_nodes).pop()

                next_lines = lines.filter(
                    Line.id.not_in(added_lines),
                    sqlalchemy.or_(Line.start_node == node, Line.end_node == node)
                ).all()

                if len(next_lines) > 0:
                    for next_line in next_lines:
                        # G.add_edge(next_line.start_node, next_line.end_node, line=next_line.id)
                        # G.add_edge(next_line.end_node, next_line.start_node, line=next_line.id)
                        G = self.__add_edges_both_directions(graph=G, node1=next_line.start_node,
                                                             node2=next_line.end_node, line=next_line)
                        open_nodes.add(next_line.start_node)
                        open_nodes.add(next_line.end_node)
                        added_lines.add(next_line.id)

                else:  # no other line of that route exists at this point
                    end_nodes.add(node)
                open_nodes.remove(node)
        else:  # in this case, the whole manipulate_geodata_and_db only exists of one line. There for the start and end node of the line
            # are the end-nodes of the graphs
            end_nodes = lines.one().nodes

        # it is possible, that an edge is still in end_nodes but it is inside the Graph with more than one edge.
        # Therefore: Check all end_nodes for their edges
        end_nodes_new = set()
        for node in end_nodes:
            edges = G.edges(node)
            if len(edges) < 2:
                end_nodes_new.add(node)
        end_nodes = end_nodes_new  # Return end_nodes

        # it is possible that an end_node has more than on connected line from the same route. In this case,
        # the endpoint is added to that Graphes, that has the node as part of it
        additional_end_nodes = self.whitelist_endpoints.get(str(route.number))
        if additional_end_nodes:
            for node in additional_end_nodes:
                if node in G.nodes:
                    end_nodes.add(node)

        # add the end_nodes to routes to nodes table
        for node_id in end_nodes:
            route.boundary_nodes.append(models.RailwayNodes.query.get(node_id))
        db.session.commit()

        remaining_lines = lines.filter(Line.id.not_in(added_lines))

        # to avoid easy turnarounds and to clear illegal connections in branches:
        nodes = list(G.nodes)  # seperate it, so it does not get changed through the creation of _create_turner
        for node_id in nodes:
            try:
                node = models.RailwayNodes.query.filter(models.RailwayNodes.id == node_id).first()
                G = self._create_turner(G=G, node=node)
            except PointOfLineNotAtEndError:
                logging.warning(
                    "For " + str(node_id) + " on route " + str(route.number) + " is not the start or end point.")

        # self._add_stations_to_route_graph(manipulate_geodata_and_db=G, route=route)

        self._check_existing_connection_route(end_nodes=end_nodes, route=route, graph=G)

        return G, remaining_lines

    def _check_all_stations_have_nodes(self, route):
        """
        controls thatt all stations have a node
        :param route:
        :return:
        """
        # TODO: Move that to models.RailwayStation
        Nodes = models.RailwayNodes
        Lines = models.RailwayLine
        points = route.railway_points
        for point in points:
            node = Nodes.check_if_nodes_exists_for_coordinate(point.coordinates)
            if not node:
                node = Nodes.add_node(point.coordinates)
                old_line = models.RailwayPoint.get_line_of_route_that_intersects_point(node.coordinate, route.number)
                newline_1, newline_2 = Lines.split_railwayline(old_line_id=old_line.id, blade_point=node.coordinate)
            elif route.number not in node.routes_number:
                old_line = models.RailwayPoint.get_line_of_route_that_intersects_point(node.coordinate, route.number)
                newline_1, newline_2 = Lines.split_railwayline(old_line_id=old_line.id, blade_point=node.coordinate)

    def _check_existing_connection_route(self, end_nodes, route, graph):
        """
        controls if a manipulate_geodata_and_db is able to route between any combination of end_nodes
        :param end_nodes:
        :return:
        """
        connections = []
        possible_routes = []
        Line = models.RailwayLine

        # creates all possible connections between all nodes.
        for start_node in end_nodes:
            start_lines = route.railway_lines.filter(
                sqlalchemy.or_(Line.start_node == start_node, Line.end_node == start_node)
            ).all()
            for end_node in end_nodes:
                if start_node == end_node:
                    continue
                else:
                    end_lines = route.railway_lines.filter(
                        sqlalchemy.or_(Line.start_node == end_node, Line.end_node == end_node)
                    ).all()
                    for combination in itertools.product(start_lines, end_lines):
                        start_line = combination[0].id
                        end_line = combination[1].id
                        try:
                            tour = self._shortest_path_nodes(graph=graph, from_node=start_node,
                                                             from_line=start_line,
                                                             to_node=end_node, to_line=end_line)
                            possible_routes.append([start_node, end_node, tour])
                        except networkx.NetworkXNoPath:
                            continue
                        except networkx.NodeNotFound as e:
                            logging.error("For route " + str(route.number) + " " + str(
                                route.name) + " a node is not part of G " + str(e))

        # iterate through all possible combinations of connections and check if there exists a allowed connection

        if not possible_routes:
            logging.warning("Route " + str(route.number) + " " + str(
                route.name) + " has no possible path between any combination of endnodes " + str(end_nodes))

        return possible_routes

    def _check_nodes_exists(self, coord, nodes_list, Model, commit_list, idlist):
        """
        Checks if a node already exists based on a list of new nodes
        :param node:
        :param nodes_list: dict with coordinate -> Model.Node
        :param model: SQLAlchemy Model of a railway_nodes table
        :commit_list: a list of open commits
        :return:
        """
        if coord in nodes_list:
            node = nodes_list[coord]
        else:
            id = self.__create_id(idlist)
            node = Model(id=id, coordinate=coord)
            commit_list.append(node)
            nodes_list[node.coordinate] = node

        return node, nodes_list, commit_list

    def __create_id(self, reference):
        """
        creates a id: Checks if a random generated id already exists in the table (table_model because sql alchemy model is needed)
        :reference: a list or dict where it checks if there is already an id.
        :return:
        """
        id = uuid.uuid4().int
        id = int(str(id)[0:6])

        while id in reference:
            id = uuid.uuid4().int
            id = int(str(id)[0:6])

        reference.append(id)

        return id

    def __add_edges_both_directions(self, graph, node1, node2, line):
        """
        add edges for both directions given the nodes and the line as edge
        :param graph:
        :param node1:
        :param node2:
        :param line:
        :return:
        """
        graph = self.add_node_to_graph(graph=graph, node_name=node1, node_data={"node_id": node1})
        graph = self.add_node_to_graph(graph=graph, node_name=node2, node_data={"node_id": node2})

        graph = self.add_edge(graph=graph, node1=node1, node2=node2, edge_data={"line": line.id})
        graph = self.add_edge(graph=graph, node1=node2, node2=node1, edge_data={"line": line.id})

        return graph

    def add_edge(self, graph, node1, node2, edge_data):
        """
        adds a edge to an manipulate_geodata_and_db.
        :param graph:
        :param node1:
        :param nod2:
        :param edge_data: dict of node_data
        :return:
        """

        # have in mind: directed manipulate_geodata_and_db!
        graph.add_edge(node1, node2, **edge_data)

        return graph

    def add_node_to_graph(self, graph, node_name, node_data):
        """
        checks if node is in manipulate_geodata_and_db, if not, it creates the node
        :param graph:
        :param node:
        :param node_data: dict of node_data
        :return:
        """

        if "node_id" not in node_data:
            raise SubnodeHasNoNodeID(
                "For manipulate_geodata_and_db " + str(graph) + " for node " + node_name + " there is no node_id"
            )

        if not node_name in graph:
            graph.add_node(node_name, **node_data)

        return graph

    def __degree_to_meter(self, degree):
        """
        Converts degree (the distance unit of srid 4326) to meter. Notice that this is an aproximation
        :return:
        """
        convertion_dict = {
            1: 111000,
            0.1: 11100,
            0.01: 1110,
            0.001: 111,
            0.0001: 11.1,
            0.00001: 1.11,
            0.000001: 0.111,
            0.0000001: 0.0111
        }

        meter = convertion_dict[degree]

        return meter

    def __meter_to_degree(self, meter):
        """
        Converts meter to degree (srid 4326). Notice that this is an approximation
        :param meter:
        :return:
        """
        convertion_dict = {
            1: 1 / 111000
        }

        degree = convertion_dict[meter]

        return degree

    def shortest_path_between_stations(self, graph, station_from, station_to, save=True, stations_via=[], filename=None):
        """
        find a path between stations. Returns list of nodes
        :param stations_via:
        :param save:
        :param graph:
        :param station_from: kuerzel of station
        :param station_to: kuerzel of station
        :return:
        """
        station_source = str(station_from) + "_out"
        station_sink = str(station_to) + "_in"

        if len(stations_via) > 0:
            pathes = []
            first_target = str(stations_via[0]) + "_in"
            first_path = super().shortest_path(graph=graph, source=station_source, target=first_target)
            pathes.extend(first_path)
            for index, station in enumerate(stations_via[:-1]):
                source_from = str(station) + "_out"
                target_to = str(stations_via[index + 1]) + "_in"
                path = super().shortest_path(graph=graph, source=source_from, target=target_to)
                pathes.extend(path)

            last_source = stations_via[-1] + "_out"
            last_path = super().shortest_path(graph=graph, source=last_source, target=station_sink)
            pathes.extend(last_path)
            path = pathes
            # lines = []

        else:
            path = super().shortest_path(graph=graph, source=station_source, target=station_sink)
            # lines = self.get_lines_of_path(graph, path)

        lines = self.get_lines_of_path(graph, path)
        station_from_long = models.RailwayStation.query.filter(
            models.RailwayStation.db_kuerzel == station_from).scalar()
        station_to_long = models.RailwayStation.query.filter(models.RailwayStation.db_kuerzel == station_to).scalar()

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

        if save:
            self._save_path(path_dict, filename=filename)

        return path_dict

    def get_lines_of_path(self, graph, path):
        """
        returns the lines that are used for the path
        :return:
        """
        lines = []
        for index, element in enumerate(path[:-1]):
            if str(element)[-2:] == "in" and str(path[index + 1])[-3:] == 'out':  # because there are no paths from station_in to station_out if station_in is first element it continues with next combination
                continue
            path_element = (element, path[index + 1])
            edge = graph.edges[path_element]
            if isinstance(edge["line"], int):
                line = edge["line"]
                lines.append(line)

            # this is last possible combination

        return lines

    def _save_path(self, path_dict, filename = None):
        """

        :return:
        """
        if filename is None:
            filepath_save = self.filepath_save_path.format(str(path_dict["source"]) + "to" + str(path_dict["sink"]))
        else:
            filepath_save = self.filepath_save_path.format(str(filename))

        path_json = json.dumps(path_dict)
        with open(filepath_save, "w") as f:
            f.write(path_json)

    def draw_map(self, graph):
        """

        :return:
        """
        nodes_pos = dict()
        for subnode in graph.nodes:
            if isinstance(subnode, int):
                node_id = graph.nodes[subnode]["node_id"]
                coordinate = models.RailwayNodes.query.get(node_id).coordinate
            elif isinstance(subnode, str):
                station_id = graph.nodes[subnode]["node_id"]
                coordinate = models.RailwayStation.query.get(station_id).coordinate_centroid
            else:
                logging.warning("For subnode " + subnode + "there is no node_id")

            nodes_pos[subnode] = coordinate

        super().show_path_on_map(graph, nodes_pos)

    def _shortest_path_nodes(self, from_node, from_line, to_node, to_line, graph):
        start_node = self._create_subnode_id(from_node, from_line, 1)
        end_node = self._create_subnode_id(to_node, to_line, 0)
        route = super().shortest_path(graph=graph, source=start_node, target=end_node)
        return route

    def check_path_exists(self, graph, from_node, to_node):
        """
        checks if a past exists
        :param graph:
        :param from_node:
        :param to_node:
        :return: bool
        """
        path_exists = False
        try:
            networkx.shortest_path(graph, from_node, to_node)
            path_exists = True
        except networkx.NetworkXNoPath:
            path_exists = False

        return path_exists
