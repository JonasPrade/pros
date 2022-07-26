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


class PointOfLineNotAtEndError(Exception):
    def __init__(self, message):
        super().__init__(message)


class RailGraph:
    def __init__(self):
        self.railgraph = networkx.Graph()

        self.filepath_whitelist_parallel_routes = os.path.abspath(
            '../example_data/railgraph/whitelist_parallel_routes.json')
        self.whitelist_parallel_routes = None

        self.filepath_whitelist_ignore_route_graph = os.path.abspath(
            '../example_data/railgraph/whitelist_ignore_route_graph.json')
        self.whitelist_ignore_route_graph = None

        self.angle_allowed_min = 60
        self.angle_allowed_max = 360 - self.angle_allowed_min

        self.ALLOWED_DISTANCE_IN_NODE = 1  # allowed distance between that are assumed to be on node [m]

        # get the whitelist for parallel railway_lines in routes:
        with open(self.filepath_whitelist_parallel_routes) as json_file:
            self.whitelist_parallel_routes = json.load(json_file)

        with open(self.filepath_whitelist_ignore_route_graph) as json_file:
            self.whitelist_ignore_route_graph = json.load(json_file)

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

        self._create_graphes_routes()

        # Create edges and nodes with networkX
        return

    def save_graph(self):
        pass

    def load_graph(self, path):
        pass

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
                node_id = self.__add_node(Nodes=Nodes, coord_railway_line=start_coord)
                db.session.query(RailwayLine).filter(RailwayLine.id == line.id).update(dict(start_node=node_id),
                                                                                       synchronize_session=False)
                db.session.commit()

            if not line.end_node:
                node_id = self.__add_node(Nodes=Nodes, coord_railway_line=end_coord)
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

            start_node, coord_dict, db_commits = self.__check_nodes_exists(coord=start_coord, nodes_list=coord_dict,
                                                                           Model=Nodes, commit_list=db_commits,
                                                                           idlist=ids)

            end_node, coord_dict, db_commits = self.__check_nodes_exists(coord=end_coord, nodes_list=coord_dict,
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
        for route in railway_routes:
            Graph = self.create_graph_route(route)

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
            G, remaining_lines = self.__build_graph_railway_line(Line, lines, route)
            graph_list.append(G)

            # There is a possibility, that not all railway lines have been used. Either because of parallel route or
            # an interrupted route
            if len(remaining_lines.all()) > 0:
                if str(route.number) in self.whitelist_parallel_routes:
                    while remaining_lines.all():
                        G, remaining_lines = self.__build_graph_railway_line(Line=Line, lines=remaining_lines,
                                                                             route=route)
                        graph_list.append(G)
                else:
                    logging.warning("For route " + str(route.number) + " " + str(
                        route.name) + " there are RailwayLines that are not part of Graph. RailwayLines are" + str(
                        remaining_lines.all()))

            return graph_list

    def _create_turner(self, G, node_input, connect_same_route=False, allow_turn_on_same_line=True):
        """
        in some nodes not all combination of edges are allowed. This function creates a sub-node where only that combination are allowed that are possibly to use.
        For that generally:
        :return:
        """
        lines = node_input.lines

        ## correct the Graph for the node.
        # Adds new edges that point to an own subnode and remove the old edges
        incoming_edges = list(G.in_edges(node_input.id))

        # TODO: u changes too and so it is wrong connected

        for u, v in incoming_edges:
            line = models.RailwayLine.query.filter(models.RailwayLine.id == G.get_edge_data(u, v)["line"]).one()
            node_u_id = self.__line_other_node(line, node_input)
            subnode_u_id = int(str(node_u_id) + str(line.id) + "1")
            subnode_v_id = int(str(node_input.id) + str(line.id) + "0")
            G.add_edge(subnode_u_id, subnode_v_id, line=line.id)

        G.remove_edges_from(incoming_edges)

        outgoing_edges = list(G.edges(node_input.id))
        for u, v in outgoing_edges:
            line = models.RailwayLine.query.filter(models.RailwayLine.id == G.get_edge_data(u, v)["line"]).one()
            node_v_id = self.__line_other_node(line, node_input)
            subnode_u_id = int(str(node_input.id) + str(line.id) + "1")
            subnode_v_id = int(str(node_v_id) + str(line.id) + "0")
            G.add_edge(subnode_u_id, subnode_v_id, line=line.id)

        G.remove_edges_from(outgoing_edges)
        G.remove_node(node_input.id)

        allowed_connections = list()
        for in_line in lines:
            for out_line in lines:
                if in_line.id == out_line.id:
                    # allow_turn_on_same_line
                    # TODO: Implement logic with a weight
                    continue
                elif in_line.route_number == out_line.route_number and connect_same_route:
                    G, allowed_connections = self.__connect_lines_turner(G=G, node=node_input, line1=in_line,
                                                                         line2=out_line,
                                                                         allowed_connections=allowed_connections)
                else:
                    angle_check = self.__get_angle_two_lines(line1=in_line, line2=out_line, node=node_input)
                    if angle_check:
                        G, allowed_connections = self.__connect_lines_turner(G=G, node=node_input, line1=in_line,
                                                                             line2=out_line,
                                                                             allowed_connections=allowed_connections)
        return G

    def __connect_lines_turner(self, G, node, line1, line2, allowed_connections):
        if not [line1, line2] in allowed_connections:
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

        :param node_id:
        :param line_id:
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
                raise PointOfLineNotAtEndError("The seachred node is not the starting or end point of line " + str(line.id))

        return next_point

    def __build_graph_railway_line(self, Line, lines, route):
        """

        :return:
        """
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

        # TODO: Add the endpoints to the nodes_to_routes

        remaining_lines = lines.filter(Line.id.not_in(added_lines))

        # to avoid easy turnarounds and to clear illegal connections in branches:
        for node_id in list(G.nodes):
            try:
                node = models.RailwayNodes.query.filter(models.RailwayNodes.id == node_id).one()
                self._create_turner(G=G, node_input=node)
            except PointOfLineNotAtEndError:
                logging.warning("For " + str(node_id) + " on route " + str(route.id) + " is not the start or end point.")

        # TODO: check if the graph is at least for one connection routable
        possible_routes = []
        try:
            for start_node in end_nodes:
                start_line = route.railway_lines.filter(
                        sqlalchemy.or_(Line.start_node == start_node, Line.end_node == start_node)
                    ).one().id
                for end_node in end_nodes:
                    if start_node == end_node:
                        continue
                    else:
                        end_line = route.railway_lines.filter(
                            sqlalchemy.or_(Line.start_node == end_node, Line.end_node == end_node)
                        ).one().id
                        try:
                            tour = self._shortest_path_nodes(graph=G, from_node=start_node, from_line=start_line, to_node=end_node, to_line=end_line)
                            possible_routes.append([start_node, end_node, tour])
                        except networkx.NetworkXNoPath:
                            continue
        except sqlalchemy.exc.MultipleResultsFound:
            logging.error('There was an error on route ' + str(route.number))

        if not possible_routes:
            logging.warning("Route " + str(route.number) + " " + str(route.name) + " has no possible path between any combination of endnodes " + str(end_nodes))

        return G, remaining_lines

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

    def __check_nodes_exists(self, coord, nodes_list, Model, commit_list, idlist):
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

    def __add_node(self, Nodes, coord_railway_line):
        node = db.session.query(Nodes).filter(Nodes.coordinate == coord_railway_line).first()
        if not node:
            # create a new node
            node = Nodes(coordinate=coord_railway_line)
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
