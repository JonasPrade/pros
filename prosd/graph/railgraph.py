import prosd.models
from prosd import models, db
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


class PointOfLineNotAtEndError(Exception):
    def __init__(self, message):
        super().__init__(message)


class RailGraph:
    def __init__(self):
        self.railgraph = networkx.DiGraph()

        self.filepath_save_graphml = '../example_data/railgraph/railgraph.pajek'

        filepath_whitelist_parallel_routes = os.path.abspath(
            '../example_data/railgraph/whitelist_parallel_routes.json')
        with open(filepath_whitelist_parallel_routes) as json_file:
            self.whitelist_parallel_routes = json.load(json_file)

        filepath_whitelist_ignore_route_graph = os.path.abspath(
            '../example_data/railgraph/whitelist_ignore_route_graph.json')
        with open(filepath_whitelist_ignore_route_graph) as json_file:
            self.whitelist_ignore_route_graph = json.load(json_file)

        filepath_whitelist_endpoints = os.path.abspath(
            '../example_data/railgraph/whitelist_endpoints.json')
        with open(filepath_whitelist_endpoints) as json_file:
            self.whitelist_endpoints = json.load(json_file)

        self.angle_allowed_min = 60
        self.angle_allowed_max = 360 - self.angle_allowed_min

        self.ALLOWED_DISTANCE_IN_NODE = self.__meter_to_degree(1)  # allowed distance between that are assumed to be on node [m]

    def create_graph(self, new_nodes=False):
        """
        Imports the RailwayLines of the db and creates a graph out of the data
        :return:
        """
        # Import RailwayLines

        # railway_lines = views.RailwayLinesSchema(many=True).dump(models.RailwayLine.query.all())
        railway_lines = models.RailwayLine.query.all()

        if new_nodes:
            self._create_nodes(railway_lines, overwrite=True)
        else:
            self.create_nodes_new_railwaylines()

        # create graphes of each route
        graph_list = self._create_graphes_routes()

        # connect graphes to one graph
        for graph in graph_list:
            self.railgraph.update(graph)

        self.save_graph(self.filepath_save_graphml, graph=self.railgraph)

        # Create edges and nodes with networkX
        return

    def save_graph(self, filepath, graph):
        networkx.write_pajek(filepath=filepath, G=graph)

    def load_graph(self, filepath):
        G = networkx.read_pajekt(filepath=filepath)
        return G

    def create_nodes_new_railwaylines(self):
        # get all railway_lines, that have no start_node or no end_node
        # check if a node already exists at that coordinate
        # if not, create a new node
        RailwayLine = models.RailwayLine
        Nodes = models.RailwayNodes

        new_lines = db.session.query(RailwayLine).filter(
            sqlalchemy.or_(RailwayLine.start_node == None, RailwayLine.end_node == None)
        ).all()

        for line in new_lines:
            wkb = shapely.wkb.loads(line.coordinates.desc, hex=True)
            start_coord, end_coord = wkb.boundary
            start_coord = shapely.wkb.dumps(start_coord, hex=True, srid=4326)
            end_coord = shapely.wkb.dumps(end_coord, hex=True, srid=4326)

            if not line.start_node:
                node_id = self.__add_node(coordinate=start_coord)
                db.session.query(RailwayLine).filter(RailwayLine.id == line.id).update(dict(start_node=node_id),
                                                                                       synchronize_session=False)
                db.session.commit()

            if not line.end_node:
                node_id = self.__add_node(coordinate=end_coord)
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

    def _create_nodes(self, railway_lines, overwrite=True):
        """
        Creates nodes based on a railway_lines (geodata)
        :param railway_lines:
        :param overwrite:
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
            db.session.query(prosd.models.RailwayLine).filter(prosd.models.RailwayLine.id == line_id).update(
                dict(start_node=nodes[0], end_node=nodes[1]),
                synchronize_session=False
            )

        db.session.commit()
        logging.info('Creation of all nodes finished')

    def _create_graphes_routes(self):
        """

        :return:
        """
        # Get all Routes
        railway_routes = models.RailwayRoute.query.all()

        # Iterate trough Routes
        graph_list = []
        for route in railway_routes:
            graph_list_route = self.create_graph_route(route)
            graph_list.append(graph_list_route)

        return graph_list

    def create_graph_route(self, route):
        """
        creates a graph for one route
        :return:
        """
        Line = models.RailwayLine
        lines = route.railway_lines
        graph_list = list()

        if len(lines.all()) == 0:
            logging.info("No railwaylines for route: " + str(route.number) + " " + str(route.name))
            return
        elif str(route.number) in self.whitelist_ignore_route_graph:
            logging.info("Route " + str(route.number) + " " + str(route.name) + " is ignored")
            return
        else:
            G, remaining_lines = self.__build_graph_railway_line(lines, route)
            graph_list.append(G)

            # There is a possibility, that not all railway lines have been used. Either because of parallel route or
            # an interrupted route
            if len(remaining_lines.all()) > 0:
                if str(route.number) in self.whitelist_parallel_routes:
                    while remaining_lines.all():
                        G, remaining_lines = self.__build_graph_railway_line(lines=remaining_lines, route=route)
                        graph_list.append(G)
                else:
                    logging.warning("For route " + str(route.number) + " " + str(
                        route.name) + " there are RailwayLines that are not part of Graph. RailwayLines are" + str(
                        remaining_lines.all()))

            return graph_list

    def _create_turner(self, G, node, connect_same_route=False, allow_turn_on_same_line=True):
        """
        in some nodes not all combination of edges are allowed. This function creates a sub-node where only that combination are allowed that are possibly to use.
        For that generally:

        :return:
        """

        G = self.__build_directed_graph_with_subnodes(G=G, node=node)
        G = self.__find_and_connect_allowed_connetions(G=G, node=node, connect_same_route=connect_same_route)

        return G

    def _remove_line_from_graph(self, G, line):
        """

        :param G: graph networkx
        :param line: a line (from model RailwayLine)
        :return:
        """
        start_node_out = self.__create_subnode_id(node_id=line.start_node, line_id=line.id, direction=1)
        start_node_in = self.__create_subnode_id(node_id=line.start_node, line_id=line.id, direction=0)
        end_node_in = self.__create_subnode_id(node_id=line.end_node, line_id=line.id, direction=0)
        end_node_out = self.__create_subnode_id(node_id=line.end_node, line_id=line.id, direction=1)

        G.remove_edge(start_node_out, end_node_in)
        G.remove_edge(end_node_out, start_node_in)

        return G

    def _add_line_to_graph(self, G, line):
        """
        adds a line to an existing graph
        :param G:
        :param line:
        :return:
        """
        # add the edges
        start_node_out = self.__create_subnode_id(node_id=line.start_node, line_id=line.id, direction=1)
        start_node_in = self.__create_subnode_id(node_id=line.start_node, line_id=line.id, direction=0)
        end_node_in = self.__create_subnode_id(node_id=line.end_node, line_id=line.id, direction=0)
        end_node_out = self.__create_subnode_id(node_id=line.end_node, line_id=line.id, direction=1)

        G.add_edge(start_node_out, end_node_in)
        G.add_edge(end_node_out, start_node_in)

        # recalculate the turner
        start_node = models.RailwayNodes.query.get(line.start_node)
        end_node = models.RailwayNodes.query.get(line.end_node)

        G = self.__find_and_connect_allowed_connetions(G=G, node=start_node)
        G = self.__find_and_connect_allowed_connetions(G=G, node=end_node)

        return G

    def __build_directed_graph_with_subnodes(self, G, node):
        """
        
        :param node: 
        :return: 
        """
        ## correct the Graph for the node.
        lines=node.lines
        # Adds new edges that point to an own subnode and remove the old edges
        incoming_edges = list(G.in_edges(node.id))

        for u, v in incoming_edges:
            line = models.RailwayLine.query.filter(models.RailwayLine.id == G.get_edge_data(u, v)["line"]).one()
            node_u_id = self.__line_other_node(line, node)
            subnode_u_id = self.__create_subnode_id(node_id=node_u_id, line_id=line.id, direction=1)
            subnode_v_id = self.__create_subnode_id(node_id=node.id, line_id=line.id, direction=0)
            G.add_edge(subnode_u_id, subnode_v_id, line=line.id)

        G.remove_edges_from(incoming_edges)

        outgoing_edges = list(G.edges(node.id))
        for u, v in outgoing_edges:
            line = models.RailwayLine.query.filter(models.RailwayLine.id == G.get_edge_data(u, v)["line"]).one()
            node_v_id = self.__line_other_node(line, node)
            subnode_u_id = self.__create_subnode_id(node_id=node.id, line_id=line.id, direction=1)
            subnode_v_id = self.__create_subnode_id(node_id=node_v_id, line_id=line.id, direction=0)
            G.add_edge(subnode_u_id, subnode_v_id, line=line.id)

        G.remove_edges_from(outgoing_edges)
        G.remove_node(node.id)

        return G

    def __find_and_connect_allowed_connetions(self, G, node, connect_same_route=False):
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
                    # allow_turn_on_same_line
                    # TODO: Implement logic with a weight
                    continue
                elif in_line.route_number == out_line.route_number and connect_same_route:
                    G, allowed_connections = self.__connect_lines_turner(G=G, node=node, line1=in_line,
                                                                         line2=out_line,
                                                                         allowed_connections=allowed_connections)
                else:
                    angle_check = self.__get_angle_two_lines(line1=in_line, line2=out_line, node=node)
                    if angle_check:
                        G, allowed_connections = self.__connect_lines_turner(G=G, node=node, line1=in_line,
                                                                             line2=out_line,
                                                                             allowed_connections=allowed_connections)

        return G

    def __connect_lines_turner(self, G, node, line1, line2, allowed_connections):
        if not [line1, line2] in allowed_connections:
            # TODO: Use the self.__create_subnode_id
            subnode_1_in = int(str(node.id) + str(line1.id) + "0")
            subnode_1_out = int(str(node.id) + str(line1.id) + "1")
            subnode_2_in = int(str(node.id) + str(line2.id) + "0")
            subnode_2_out = int(str(node.id) + str(line2.id) + "1")
            G.add_edge(subnode_1_in, subnode_2_out)
            G.add_edge(subnode_2_in, subnode_1_out)
            allowed_connections.append([line1, line2])
        return G, allowed_connections

    def __get_angle_two_lines(self, line1, line2, node):
        angle_check = False
        line1_point = self.__next_point_of_line(line=line1, point=node.coordinate)
        line2_point = self.__next_point_of_line(line=line2, point=node.coordinate)
        statement = db.session.query(geoalchemy2.func.ST_Angle(node.coordinate, line1_point, node.coordinate,
                                                               line2_point))  # 2 times node.coordinate so it is node - line1 to node - line2
        angle = math.degrees(db.session.execute(statement).one()[0])
        if self.angle_allowed_min < angle < self.angle_allowed_max:
            angle_check = True
        return angle_check

    def _shortest_path_nodes(self, from_node, from_line, to_node, to_line, graph):
        start_node = self.__create_subnode_id(from_node, from_line, 1)
        end_node = self.__create_subnode_id(to_node, to_line, 0)
        route = self.__shortest_path(graph=graph, source=start_node, target=end_node)
        return route

    def __shortest_path(self, graph, source, target):
        route = networkx.shortest_path(G=graph, source=source, target=target)  # TODO: Add weight function
        return route

    def __create_subnode_id(self, node_id, line_id, direction):
        """

        :param node_id: int id of node
        :param line_id: int id of line
        :param direction: int 0 or 1
        :return:
        """
        # TODO: Change all creation of subnodes_id to this function
        subnode_id = int(str(node_id)+str(line_id)+str(direction))
        return subnode_id

    def __next_point_of_line(self, line, point):
        """
        Gets the next point of an line.
        :param line:
        :param point:
        :return:
        """
        line_points = db.session.execute(db.session.query(geoalchemy2.func.ST_DumpPoints(line.coordinates))).all()
        line_start = db.session.execute(db.session.query(geoalchemy2.func.ST_StartPoint(line.coordinates))).one()[0]
        line_end = db.session.execute(db.session.query(geoalchemy2.func.ST_EndPoint(line.coordinates))).one()[0]

        if point == line_start:
            next_point = line_points[1][0].split(',')[1][:-1]
        elif point == line_end:
            next_point = line_points[-2][0].split(',')[1][:-1]
        else:
            if db.session.execute(db.session.query(geoalchemy2.func.ST_DWithin(point, line_start, self.ALLOWED_DISTANCE_IN_NODE))).one()[0]:
                next_point = line_points[1][0].split(',')[1][:-1]
            elif db.session.execute(db.session.query(geoalchemy2.func.ST_DWithin(point, line_end, self.ALLOWED_DISTANCE_IN_NODE))).one()[0]:
                next_point = line_points[-2][0].split(',')[1][:-1]
            else:
                raise PointOfLineNotAtEndError("The searched node is not the starting or end point of line " + str(line.id))

        return next_point

    def __build_graph_railway_line(self, lines, route):
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
        G.add_edge(first_line.start_node, first_line.end_node, line=first_line.id)
        G.add_edge(first_line.end_node, first_line.start_node, line=first_line.id)

        open_nodes.add(first_line.start_node)
        open_nodes.add(first_line.end_node)
        added_lines.add(first_line.id)

        if len(lines.all()) > 1:
            while open_nodes:
                node = list(open_nodes).pop()

                next_lines = lines.filter(
                    Line.id.not_in(added_lines),
                    sqlalchemy.or_(Line.start_node == node, Line.end_node == node)
                ).all()

                if len(next_lines) > 0:
                    for next_line in next_lines:
                        G.add_edge(next_line.start_node, next_line.end_node, line=next_line.id)
                        G.add_edge(next_line.end_node, next_line.start_node, line=next_line.id)
                        open_nodes.add(next_line.start_node)
                        open_nodes.add(next_line.end_node)
                        added_lines.add(next_line.id)

                else:  # no other line of that route exists at this point
                    end_nodes.add(node)
                open_nodes.remove(node)
        else: # in this case, the whole graph only exists of one line. There for the start and end node of the line are the end-nodes of the graphs
            end_nodes = lines.one().nodes

        # it is possible, that an edge is still in end_nodes but it is inside the Graph with more than one edge.
        # Therefore: Check all end_nodes for their edges
        end_nodes_new = set()
        for node in end_nodes:
            edges = G.edges(node)
            if len(edges) < 2:
                end_nodes_new.add(node)

        end_nodes = end_nodes_new  # Return end_nodes

        # it is possible that an end_node has more than on connected line from the same route. In this case, the endpoint is added to that Graphes, that has the node as part of it
        additional_end_nodes = self.whitelist_endpoints.get(str(route.number))
        if additional_end_nodes:
            for node in additional_end_nodes:
                if node in G.nodes:
                    end_nodes.add(node)

        # add the end_nodes to routes to nodes
        for node_id in end_nodes:
            route.end_nodes.append(models.RailwayNodes.query.get(node_id))
        db.session.commit()

        remaining_lines = lines.filter(Line.id.not_in(added_lines))

        # to avoid easy turnarounds and to clear illegal connections in branches:
        nodes = list(G.nodes)  # seperate it, so it does not get changed through the creation of _create_turner
        for node_id in nodes:
            try:
                node = models.RailwayNodes.query.filter(models.RailwayNodes.id == node_id).first()
                G = self._create_turner(G=G, node=node)
            except PointOfLineNotAtEndError:
                logging.warning("For " + str(node_id) + " on route " + str(route.number) + " is not the start or end point.")

        self.__check_existing_connection_route(end_nodes=end_nodes, route=route, graph=G)

        return G, remaining_lines

    def __check_existing_connection_route(self, end_nodes, route, graph):
        """

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
                            logging.error("For route " + str(route.number) + " " + str(route.name) + " a node is not part of G " + str(e))

        # iterate through all possible combinations of connections and check if there exists a allowed connection

        if not possible_routes:
            logging.warning("Route " + str(route.number) + " " + str(
                route.name) + " has no possible path between any combination of endnodes " + str(end_nodes))

        return possible_routes

    def __line_other_node(self, line, node1):
        """
        returns the other end/start node of the line depending on the input node
        :param line:
        :return:
        """
        line_nodes = line.nodes
        line_nodes.remove(node1.id)
        node2_id = line_nodes[0]

        return node2_id

    def _connect_end_node_to_line(self, G_of_node, G_continuing_line, node, line_of_node):
        """

        :return:
        """
        # get the line which intersects the endpoint
        line = self._find_line_intersects_point(coordinate=node.coordinate, from_line=line_of_node)

        G_continuing_line = self._remove_line_from_graph(G=G_continuing_line, line=line)

        # split the line which intersects the endpoint
        newline1, newline2 = self._split_railway_lines(old_line_id=line.id, blade_point=node.coordinate)

        G_continuing_line = self._add_line_to_graph(G=G_continuing_line, line=newline1)
        G_continuing_line = self._add_line_to_graph(G=G_continuing_line, line=newline2)

        # connect the graphes together
        G_continuing_line.update(G_of_node)
        G_continuing_line = self.__find_and_connect_allowed_connetions(G=G_continuing_line, node=node)

        return G_continuing_line

    def _find_line_intersects_point(self, coordinate, from_line):
        """

        :param coordinate: coordinates in wkb string
        :param from_line: defines a line where the coordinate is from so this line gets ignored
        :return:
        """
        line = models.RailwayLine.query.filter(geoalchemy2.func.ST_Intersects(models.RailwayLine.coordinates, coordinate), models.RailwayLine.id != from_line.id).one()

        return line

    def _split_railway_lines(self, old_line_id, blade_point):
        """

        :param line: id of line that gets splitted
        :param blade_point: point where the railway_line gets splitted (wkb)
        :return:
        """
        old_line = models.RailwayLine.query.filter(models.RailwayLine.id == old_line_id).one()

        # get the coordinates
        # TODO: Not all rail station are directly on the line

        # not all rail stations/blade points are dirctly on the line. So this algorithmus searches the clostes point on the linestring.

        coordinates = db.session.execute(
            db.session.query(
                geoalchemy2.func.ST_Dump(
                    geoalchemy2.func.ST_CollectionExtract(
                        geoalchemy2.func.ST_Split(old_line.coordinates, blade_point)
                    )
                )
            )
            ).all()

        if len(coordinates) != 2:
            coordinates = None
            # a split was not possible.
            # create a line from the blade_point with a mirrod blade_point on the line

            # get the closest point on the line
            # but even then, sometimes the split doesnt work so...
            blade_point_on_line = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_ClosestPoint(
                        old_line.coordinates,
                        blade_point),
                )
            ).one()[0]

            # get the mirrod point
            blade_point_reversed = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_Rotate(
                    blade_point,
                    3.14,
                    blade_point_on_line)
                )
            ).one()[0]

            blade_line = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_MakeLine(
                        blade_point,
                        blade_point_reversed
                    )
                )
            ).one()[0]

            # blade_point_reversed_wkt = shapely.wkb.loads(blade_point_reversed.desc, hex=True)
            # b_wkt = shapely.wkb.loads(blade_point_on_line.desc, hex=True)
            blade_line_wkt = shapely.wkb.loads(blade_line.desc, hex=True)

            coordinates = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_Dump(
                        geoalchemy2.func.ST_CollectionExtract(
                            geoalchemy2.func.ST_Split(old_line.coordinates, blade_line)
                        )
                    )
                )
            ).all()

        coordinates_newline_1 = coordinates[0]
        coordinates_newline_2 = coordinates[1]

        # TODO: Throw error if there is a third linestring in the geometry collection

        newline_1 = self.__create_new_railline_from_oldline(line_old=old_line, coordinates=coordinates_newline_1)
        newline_2 = self.__create_new_railline_from_oldline(line_old=old_line, coordinates=coordinates_newline_2)

        db.session.delete(old_line)
        db.session.commit()

        return newline_1, newline_2

    def __create_new_railline_from_oldline(self, line_old, coordinates):
        """

        :param line_old: a object of an existing line, all attributes will be cloned
        :param coordinates: coordinates of the new line (LINESTRING)
        :return:
        """
        # have in mind, that all attribute are copied, also the kilometer distance from DB. This is because it is not always the length of the line.

        coordinates = coordinates[0].split(",")[1][:-1]
        coordinates_wkb = db.session.execute(db.session.query(geoalchemy2.func.ST_Force2D(coordinates))).one()[0]

        railline = models.RailwayLine(
            coordinates=coordinates_wkb,
            route_number=line_old.route_number,
            direction=line_old.direction,
            length=line_old.length,
            from_km=line_old.from_km,
            to_km=line_old.to_km,
            electrified=line_old.electrified,
            number_tracks=line_old.number_tracks,
            vmax=line_old.vmax,
            type_of_transport=line_old.type_of_transport,
            bahnart=line_old.bahnart,
            strecke_kuerzel=line_old.strecke_kuerzel,
            active_until=line_old.active_until,
            active_since=line_old.active_since,
            railway_infrastructure_company=line_old.railway_infrastructure_company
        )

        railline_start_coordinate = db.session.execute(db.session.query(geoalchemy2.func.ST_StartPoint(coordinates_wkb))).one()[0]
        railline.start_node = self.__add_node(railline_start_coordinate)
        railline_end_coordinates = db.session.execute(db.session.query(geoalchemy2.func.ST_EndPoint(coordinates_wkb))).one()[0]
        railline.end_node = self.__add_node(railline_end_coordinates)

        db.session.add(railline)
        db.session.commit()

        return railline

    def _check_nodes_exists(self, coord, nodes_list, Model, commit_list, idlist):
        """
        Checks if a node already exists
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

    def __add_node(self, coordinate):
        """
        checks if for the given coordinate a nodes exists (tolerance included). If not, a new node gets created.
        :param coordinate: wkb element coordinate
        :return:
        """
        Nodes = models.RailwayNodes

        # TODO: Check why this is necessary
        # if not isinstance(coordinate, str):
        #     coordinate = db.session.execute(
        #         db.session.query(
        #         geoalchemy2.func.ST_GeogFromWKB(coordinate)
        #         )).one()[0]

        node = Nodes.query.filter(geoalchemy2.func.ST_DWithin(models.RailwayNodes.coordinate, coordinate, self.ALLOWED_DISTANCE_IN_NODE)).first()

        # check if coordinate is 2d. If this is case, make it 3 dimensional
        coordinate_dimensions = db.session.execute(
            db.session.query(
                geoalchemy2.func.ST_NDims(coordinate)
            )
        ).one()[0]
        if coordinate_dimensions == 2:
            x = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_X(coordinate)
                )
            ).one()[0]
            y = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_Y(coordinate)
                )
            ).one()[0]
            z = 0
            coordinate = db.session.execute(
                db.session.query(
                    geoalchemy2.func.ST_MakePoint(x, y, z)
                )
            ).one()[0]

        if not node:
            # create a new node
            node = Nodes(coordinate=coordinate)
            db.session.add(node)
            db.session.commit()
            db.session.refresh(node)

        return node.id

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
            1: 1/111000
        }

        degree = convertion_dict[meter]

        return degree