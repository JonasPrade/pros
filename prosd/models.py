import datetime
import jwt
import geojson
import geoalchemy2
import shapely
import sqlalchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.associationproxy import association_proxy
import math
import logging

from prosd import db, app, bcrypt


class PointOfLineNotAtEndError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoSplitPossibleError(Exception):
    def __init__(self, message):
        super().__init__(message)

# TODO: Table railway_line to projects

# allowed_values_type_of_station = conf.allowed_values_type_of_station  # TODO: Add enum to type of station

# be careful: no index of geo-coordinates of states and counties

# m:n tables

# project to group
# TODO: Change that to projectcontent
projectcontent_to_group = db.Table('projectcontent_to_group',
                            db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id')),
                            db.Column('projectgroup_id', db.Integer, db.ForeignKey('project_groups.id'))
                            )

# project to railway Lines
projectcontent_to_line = db.Table('projectcontent_to_lines',
                           db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id')),
                           db.Column('railway_lines_id', db.Integer, db.ForeignKey('railway_lines.id'))
                           )

# project to railway points
project_to_railway_points = db.Table('projects_to_points',
                                     db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
                                     db.Column('railway_point_id', db.Integer, db.ForeignKey('railway_points.id')),
                                     )

texts_to_project_content = db.Table('texts_to_projects',
                                    db.Column('project_content_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                    db.Column('text_id', db.Integer, db.ForeignKey('texts.id'))
                                    )


project_contents_to_states = db.Table('projectcontent_to_states',
                                      db.Column('project_content_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                      db.Column('states_id', db.Integer, db.ForeignKey('states.id'))
                                    )

project_contents_to_counties = db.Table('projectcontent_to_counties',
                                        db.Column('project_content_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                        db.Column('counties_id', db.Integer, db.ForeignKey('counties.id'))
                                        )

project_contents_to_constituencies = db.Table('projectcontent_to_constituencies',
                                              db.Column('project_content_id',db.Integer, db.ForeignKey('projects_contents.id')),
                                              db.Column('constituencies_id', db.Integer, db.ForeignKey('constituencies.id'))
                                              )

railway_nodes_to_railway_routes = db.Table('nodes_to_routes',
                           db.Column('node_id', db.Integer, db.ForeignKey('railway_nodes.id')),
                           db.Column('route_id', db.Integer, db.ForeignKey('railway_route.id'))
                           )

# classes/Tables


class RailwayLine(db.Model):
    """
    defines a RailwayLine, which is part of a railway network and has geolocated attributes (Multiline oder Line).
    The RailwayLine are small pieces of rail, because they can quickly change attributes like allowed speed.
    A RailwayLine is part of a RailRoute (German: VzG)
    """
    # TODO: Check if this RailwayLine can be used for import RailML infrastructure

    __tablename__ = 'railway_lines'
    id = db.Column(db.Integer, primary_key=True)
    mifcode = db.Column(db.String(30))  # MapInfo-interne Objektbezeichnung
    route_number = db.Column(db.Integer, db.ForeignKey('railway_route.number', onupdate='CASCADE', ondelete='SET NULL'))
    direction = db.Column(db.Integer)
    length = db.Column(db.Integer)
    from_km = db.Column(db.Integer)
    to_km = db.Column(db.Integer)
    electrified = db.Column(db.String(20))  # Add allowed values: Oberleitung, nicht elektrifiziert, Stromschiene
    number_tracks = db.Column(db.String(100))  # eingleisig, zweigleisig
    vmax = db.Column(db.String(20))
    type_of_transport = db.Column(db.String(20))  # Pz-Bahn, Gz- Bahn, Pz/Gz-Bahn, S-Bahn, Hafenbahn, Seilzugbahn
    strecke_kuerzel = db.Column(db.String(100))
    bahnart = db.Column(db.String(100))
    active_until = db.Column(db.Integer)
    active_since = db.Column(db.Integer)
    coordinates = db.Column(geoalchemy2.Geometry(geometry_type='LINESTRING', srid=4326), nullable=False)
    railway_infrastructure_company = db.Column(db.Integer, db.ForeignKey('railway_infrastructure_company.id', ondelete='SET NULL'))

    # graph
    start_node = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', ondelete='SET NULL'))
    end_node = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', ondelete='SET NULL'))

    def __init__(self, coordinates, route_number=None, direction=0, length=None, from_km=None, to_km=None, electrified=None,
                 number_tracks=None, vmax=None, type_of_transport=None, bahnart=None,
                 strecke_kuerzel=None, active_until=None, active_since=None, railway_infrastructure_company=None):
        self.route_number = route_number
        self.direction = direction
        self.length = length
        self.from_km = from_km
        self.to_km = to_km
        self.electrified = electrified
        self.number_tracks = number_tracks
        self.vmax = vmax
        self.type_of_transport = type_of_transport
        self.strecke_kuerzel = strecke_kuerzel
        self.bahnart = bahnart
        self.active_until = active_until
        self.active_since = active_since
        self.coordinates = coordinates
        self.railway_infrastructure_company = railway_infrastructure_company

    @hybrid_property
    def nodes(self):
        nodes = []
        nodes.append(self.start_node)
        nodes.append(self.end_node)
        return nodes

    @classmethod
    def geojson(self, obj):
        coords = geoalchemy2.shape.to_shape(obj.coordinates)
        xy = coords.xy
        x_array = xy[0]
        y_array = xy[1]
        coords_geojson = []

        for x, y in zip(x_array, y_array):
            coords_geojson.append((x, y))

        geo = geojson.LineString(coords_geojson)
        return geo

    @classmethod
    def create_railline_from_old(self, line_old, coordinates):
        """
        :param line_old: a object of an existing line, all attributes will be cloned
        :param coordinates: coordinates of the new line (LINESTRING)
        :return:
        """
        # have in mind, that all attribute are copied, also the kilometer distance from DB. This is because it is not always the length of the line.

        if isinstance(coordinates, str):
            coordinates = coordinates.split(",")[1][:-1]
            coordinates_wkb = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_Force2D(coordinates))).one()[0]
        else:
            coordinates_wkb = coordinates

        railline = RailwayLine(
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

        railline_start_coordinate = \
        db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_StartPoint(coordinates_wkb))).one()[0]
        railline.start_node = RailwayNodes.add_node_if_not_exists(railline_start_coordinate).id
        railline_end_coordinates = \
        db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_EndPoint(coordinates_wkb))).one()[0]
        railline.end_node = RailwayNodes.add_node_if_not_exists(railline_end_coordinates).id

        db.session.add(railline)
        db.session.commit()

        return railline

    @classmethod
    def split_railwayline(self, old_line_id, blade_point):
        """
        :param line: id of line that gets splitted
        :param blade_point: point where the railway_line gets splitted (wkb)
        :return:
        """
        old_line = RailwayLine.query.filter(RailwayLine.id == old_line_id).one()

        coordinates = db.session.execute(
            sqlalchemy.select(
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
                sqlalchemy.select(
                    geoalchemy2.func.ST_ClosestPoint(
                        old_line.coordinates,
                        blade_point),
                )
            ).one()[0]

            # get the mirrod point
            blade_point_reversed = db.session.execute(
                sqlalchemy.select(
                    geoalchemy2.func.ST_Rotate(
                        blade_point,
                        3.14,
                        blade_point_on_line)
                )
            ).one()[0]

            blade_line = db.session.execute(
                sqlalchemy.select(
                    geoalchemy2.func.ST_MakeLine(
                        blade_point,
                        blade_point_reversed
                    )
                )
            ).one()[0]

            # for debugging
            # blade_point_reversed_wkt = shapely.wkb.loads(blade_point_reversed.desc, hex=True)
            # b_wkt = shapely.wkb.loads(blade_point_on_line.desc, hex=True)
            # blade_line_wkt = shapely.wkb.loads(blade_line.desc, hex=True)

            coordinates = db.session.execute(
                sqlalchemy.select(
                    geoalchemy2.func.ST_Dump(
                        geoalchemy2.func.ST_CollectionExtract(
                            geoalchemy2.func.ST_Split(old_line.coordinates, blade_line)
                        )
                    )
                )
            ).all()

        if len(coordinates) != 2:
            coordinates = None

            buffer = db.session.execute(
                sqlalchemy.select(
                    geoalchemy2.func.ST_Buffer(
                        blade_point,
                        1/80000000
                    )
                )
            ).scalar()

            coordinates = db.session.execute(
                sqlalchemy.select(
                    geoalchemy2.func.ST_Dump(
                        geoalchemy2.func.ST_CollectionExtract(
                            geoalchemy2.func.ST_Split(old_line.coordinates, buffer)
                        )
                    )
                )
            ).all()

            # TODO: add coordinate 1 und 2 to one coordinate

        if len(coordinates) < 2 or len(coordinates) >3:
            raise NoSplitPossibleError(
                "For line " + str(old_line.id) + " at point " + str(shapely.wkb.loads(blade_point.desc, hex=True)) + " not possible"
            )
        elif len(coordinates) == 2:
            coordinates_newline_1 = coordinates[0][0]
            coordinates_newline_2 = coordinates[1][0]
        elif len(coordinates) == 3:
            coordinates_1 = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_Force2D(coordinates[0][0].split(",")[1][:-1]))).scalar()
            coordinates_2 = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_Force2D(coordinates[1][0].split(",")[1][:-1]))).scalar()

            coordinates_newline_1 = db.session.execute(
                db.select(
                    geoalchemy2.func.ST_LineMerge(
                        geoalchemy2.func.ST_Union(
                            coordinates_1,
                            coordinates_2
                        )
                    )
                )
            ).scalar()
            coordinates_newline_2 = coordinates[2][0]

        # TODO: Throw error if there is a third linestring in the geometry collection

        newline_1 = self.create_railline_from_old(line_old=old_line, coordinates=coordinates_newline_1)
        newline_2 = self.create_railline_from_old(line_old=old_line, coordinates=coordinates_newline_2)

        db.session.delete(old_line)
        db.session.commit()

        return newline_1, newline_2

    @classmethod
    def get_line_that_intersects_point_excluding_line(self, coordinate, from_line):
        """
        :param coordinate: coordinates in wkb string
        :param from_line: defines a line where the coordinate is from so this line gets ignored
        :return:
        """
        line = RailwayLine.query.filter(
            geoalchemy2.func.ST_Intersects(RailwayLine.coordinates, coordinate),
            RailwayLine.id != from_line.id).one()

        return line

    @classmethod
    def get_other_node_of_line(self, line, node1_id):
        """
        returns the other end/start node of the line depending on the input node
        :param line:
        :return:
        """
        # TODO: Change that, so it can be called as attribute of an RailwayLine instance
        line_nodes = line.nodes
        line_nodes.remove(node1_id)
        node2_id = line_nodes[0]
        node_2 = RailwayNodes.query.get(node2_id)

        return node_2

    @classmethod
    def get_next_point_of_line(self, line, point, allowed_distance = 1/222000):
        """
        Gets the next point of an line.
        :param line:
        :param point:
        :return:
        """

        line_points = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_DumpPoints(line.coordinates))).all()
        line_start = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_StartPoint(line.coordinates))).one()[0]
        line_end = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_EndPoint(line.coordinates))).one()[0]

        if point == line_start:
            next_point = line_points[1][0].split(',')[1][:-1]
        elif point == line_end:
            next_point = line_points[-2][0].split(',')[1][:-1]
        else:
            if db.session.execute(sqlalchemy.select(
                    geoalchemy2.func.ST_DWithin(point, line_start, allowed_distance))).one()[0]:
                next_point = line_points[1][0].split(',')[1][:-1]
            elif db.session.execute(sqlalchemy.select(
                    geoalchemy2.func.ST_DWithin(point, line_end, allowed_distance))).one()[0]:
                next_point = line_points[-2][0].split(',')[1][:-1]
            else:
                raise PointOfLineNotAtEndError(
                    "The searched node is not the starting or end point of line " + str(line.id))

        return next_point

    @classmethod
    def get_angle_two_lines(self, line1, line2, node, angle_allowed_min=60):
        angle_allowed_max = 360 - angle_allowed_min

        angle_check = False

        line1_point = RailwayLine.get_next_point_of_line(line=line1, point=node.coordinate)
        line2_point = RailwayLine.get_next_point_of_line(line=line2, point=node.coordinate)
        angle_rad = db.session.execute(sqlalchemy.select(
            geoalchemy2.func.ST_Angle(node.coordinate, line1_point, node.coordinate,
                                                                       line2_point))).one()[
            0]  # 2 times node.coordinate so it is node - line1 to node - line2

        if angle_rad is not None:
            angle = math.degrees(angle_rad)
            if angle_allowed_min < angle < angle_allowed_max:
                angle_check = True
        else:
            logging.warning("Could not calculate angle(radian) for " + str(line1.id) + " and " + str(line2.id) + " angle rad is " + str(angle_rad))
        return angle_check


class RailwayPoint(db.Model):
    __tablename__ = 'railway_points'
    id = db.Column(db.Integer, primary_key=True)
    mifcode = db.Column(db.String(255))
    station_id = db.Column(db.Integer, db.ForeignKey('railway_stations.id', ondelete='SET NULL'))
    route_number = db.Column(db.Integer, db.ForeignKey('railway_route.number', onupdate='CASCADE', ondelete='SET NULL'))
    richtung=db.Column(db.Integer)
    km_i = db.Column(db.Integer)
    km_l = db.Column(db.String(255))
    name = db.Column(db.String(255))
    type = db.Column(db.String(255))  # db.Enum(allowed_values_type_of_station)
    db_kuerzel = db.Column(db.String(5))
    coordinates = db.Column(geoalchemy2.Geometry(geometry_type='POINTZ', srid=4326), nullable=False)
    node_id = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', onupdate='CASCADE', ondelete='SET NULL'))

    # TODO: Connect that to DB Station Names, have in mind that we also have some Non-DB-stations

    # References
    # projects_start = db.relationship('Project', backref='project_starts', lazy=True)
    # projects_end = db.relationship('Project', backref='project_ends', lazy=True)

    @classmethod
    # TODO: Write test
    # TODO: Move that to an class that inherits point, node and station
    def get_line_of_route_that_intersects_point(self, coordinate, route_number, allowed_distance_in_node=1/2220000):
        """

        :param coordinate:
        :param route_number:
        :param allowed_distance_in_node:
        :return:
        """
        try:
            line = RailwayLine.query.filter(
                geoalchemy2.func.ST_DWithin(RailwayLine.coordinates, coordinate, allowed_distance_in_node),
                RailwayLine.route_number == route_number
            ).one()
        except sqlalchemy.exc.NoResultFound:
            allowed_distance_in_node = allowed_distance_in_node*10
            line = RailwayLine.query.filter(
                geoalchemy2.func.ST_DWithin(RailwayLine.coordinates, coordinate, allowed_distance_in_node),
                RailwayLine.route_number == route_number
            ).one()

        return line


class RailwayStation(db.Model):
    """
    a railway point is always connected with one route. The station collects all railway_points of the same station
    """
    __tablename__ = 'railway_stations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    db_kuerzel = db.Column(db.String(5), unique=True)
    type = db.Column(db.String(10))

    railway_points = db.relationship("RailwayPoint", lazy="dynamic")
    railway_nodes = db.relationship("RailwayNodes", secondary="join(RailwayPoint, RailwayNodes, RailwayPoint.node_id == RailwayNodes.id)", viewonly=True)


    @hybrid_property
    def railway_lines(self):
        nodes = self.railway_nodes
        railway_lines = []
        for node in nodes:
            lines = node.lines
            for line in lines:
                railway_lines.append(line)

        return railway_lines

    @hybrid_property
    def coordinate_centroid(self):
        """
        calculate the coordinate at centroid of the coordinates of the points connected to the stations
        :return:
        """
        points = self.railway_points.all()
        coord_list = []

        for point in points:
            coord = point.coordinates.desc
            coord_list.append(coord)

        coordinates = db.session.execute(
            db.select(
                geoalchemy2.func.ST_Union(coord_list)
            )
        ).scalar()
        
        coordinate_centroid = db.session.execute(
            db.select(
                geoalchemy2.func.ST_Centroid(coordinates)
            )
        ).scalar()
        
        return coordinate_centroid


class RailwayNodes(db.Model):
    """
    keeps all nodes for the railway network to create a network graph
    """
    __tablename__='railway_nodes'
    id = db.Column(db.Integer, primary_key=True)
    coordinate = db.Column(geoalchemy2.Geometry(geometry_type='POINTZ', srid=4326), nullable=False)

    start_lines = db.relationship('RailwayLine', lazy=True, foreign_keys="[RailwayLine.start_node]")
    end_lines = db.relationship('RailwayLine', lazy=True, foreign_keys="[RailwayLine.end_node]")

    point = db.relationship('RailwayPoint', lazy=True)

    @hybrid_property
    def lines(self):
        lines = []
        for line in self.start_lines:
            lines.append(line)

        for line in self.end_lines:
            lines.append(line)

        return lines

    @hybrid_property
    def routes_number(self):
        routes_number = set()
        for line in self.lines:
            routes_number.add(line.route_number)

        return routes_number

    @classmethod
    def add_node_if_not_exists(self, coordinate, allowed_distance_in_node=1/222000):
        """
        checks if for the given coordinate a nodes exists (tolerance included). If not, a new node gets created.
        :param coordinate: wkb element coordinate
        :return:
        """
        coordinate = self.coordinate_check_to_wkb(coordinate)
        node = self.check_if_nodes_exists_for_coordinate(coordinate, allowed_distance_in_node)
        if not node:
            node = self.add_node(coordinate)

        return node

    @classmethod
    def coordinate_check_to_wkb(self, coordinate):
        """
        checks if a coordinate is wkb, if not it converts it to wkb
        :return:
        """
        # TODO: Move that to a BaseClasse, so all models can use it
        if isinstance(coordinate, shapely.geometry.Point):
            coordinate = shapely.wkb.dumps(coordinate)

        # TODO: Move that to models.RailwayNode
        # TODO: Check why this is necessary
        # if not isinstance(coordinate, str):
        #     coordinate = db.session.execute(
        #         db.session.query(
        #         geoalchemy2.func.ST_GeogFromWKB(coordinate)
        #         )).one()[0]

        return coordinate

    @classmethod
    def check_if_nodes_exists_for_coordinate(self, coordinate, allowed_distance_in_node = 1/222000):
        """

        :param coordinate:
        :param allowed_distance_in_node:
        :return node: models.RailwayNode, if there is no node it returns a None
        """
        try:
            node = RailwayNodes.query.filter(geoalchemy2.func.ST_DWithin(RailwayNodes.coordinate, coordinate,
                                                              allowed_distance_in_node)).scalar()
        except sqlalchemy.exc.MultipleResultsFound:
            allowed_distance_in_node = allowed_distance_in_node*(1/100)
            node = RailwayNodes.query.filter(geoalchemy2.func.ST_DWithin(RailwayNodes.coordinate, coordinate,
                                                                         allowed_distance_in_node)).scalar()

        return node

    @classmethod
    def add_node(self, coordinate):
        """

        :param coordinate: wkb
        :return:
        """
        # check if coordinate is 2d. If this is case, make it 3 dimensional
        coordinate_dimensions = db.session.execute(
            sqlalchemy.select(
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

        # create a new node
        node = RailwayNodes(coordinate=coordinate)
        db.session.add(node)
        db.session.commit()
        db.session.refresh(node)

        return node

    @classmethod
    def get_line_for_node_and_route(self, node_id, route_number):
        """
        gets all lines for an route that are connected to a node
        (for example all lines that are connected with an end-node of that line)
        :param node:
        :param route:
        :return:
        """
        lines = RailwayLine.query.filter(
            sqlalchemy.or_(
                node_id == RailwayLine.start_node,
                node_id == RailwayLine.end_node
            ),
            RailwayLine.route_number == route_number
        ).all()

        return lines

    @classmethod
    def get_line_for_node_and_other_routes(self, node_id, route_number):
        """
        gets all lines that are connect to that line and that are not part of the route
        :param node_id:
        :param route_number:
        :return:
        """
        lines = RailwayLine.query.filter(
            sqlalchemy.or_(
                node_id == RailwayLine.start_node,
                node_id == RailwayLine.end_node
            ),
            RailwayLine.route_number != route_number
        ).all()

        return lines

    @classmethod
    def get_other_routes_for_node(self, node_id, route_number):
        """
        get all other routes that are connect to that node via at least one line
        :param node_id:
        :return:
        """
        routes_on_node = db.session.query(RailwayRoute).join(RailwayLine).filter(
            sqlalchemy.or_(
                RailwayLine.end_node == node_id,
                RailwayLine.start_node == node_id
            ),
            RailwayRoute.number != route_number
        ).all()

        return routes_on_node


class RailwayRoute(db.Model):
    """
    German: VzG-Strecken
    """
    __tablename__ = 'railway_route'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True)  # for example the VzG-number
    name = db.Column(db.String(255))
    infotext = db.Column(db.Text)
    start_km = db.Column(db.Float)
    end_km = db.Column(db.Float)

    railway_lines = db.relationship("RailwayLine", backref="railway_routes", lazy="dynamic")

    boundary_nodes = db.relationship("RailwayNodes", secondary=railway_nodes_to_railway_routes,
                               backref=db.backref('railway_route_ending', lazy=True))

    railway_points = db.relationship("RailwayPoint", lazy=True)

    # TODO: m:n Project_Contents to RailwayRoutes

    @hybrid_property
    def coordinates(self):

        lines = self.railway_lines.all()
        coord_list = []

        for line in lines:
            coord = line.coordinates.desc
            coord_list.append(coord)

        coordinates = db.session.execute(
            db.select(
                geoalchemy2.func.ST_Union(coord_list)
            )
        ).scalar()

        return coordinates

    @classmethod
    def get_nodes_whose_endpoints_on_input_route(self, input_route):
        """
        gets all coordinates from nodes of routes whose endpoints lies on the given route.
        :param input_route:
        :return:
        """
        all_nodes = RailwayNodes.query.filter(
            geoalchemy2.func.ST_Intersects(input_route.coordinates, RailwayNodes.coordinate),
        ).all()

        nodes = list()
        for node in all_nodes:
            if input_route.number not in node.routes_number:
                nodes.append(node)

        return nodes

class RailwayInfrastructureCompany(db.Model):
    """

    """
    __tablename__ = "railway_infrastructure_company"
    id = db.Column(db.Integer, primary_key=True)
    name_short = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)

    # TODO: Set all to DB Netz that are not to some company else.


class Project(db.Model):
    """
    defines a Project which can be related with (different) project contents and is connected m:n to RailwayLine
    """
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    # id_point_start_id = db.Column(db.Integer, db.ForeignKey('railway_points.id'))
    # id_point_end_id = db.Column(db.Integer, db.ForeignKey('railway_points.id'))
    superior_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))  # TODO: Change that to project_content

    # references
    project_contents = db.relationship('ProjectContent', backref='project', lazy=True)
    superior_project = db.relationship("Project", backref='sub_project', remote_side=id)

    def __init__(self, name, description='', superior_project_id=None):
        self.name = name
        self.description = description
        self.superior_project = superior_project_id


class ProjectContent(db.Model):
    __tablename__ = 'projects_contents'

    # Basic informations
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    project_number = db.Column(db.String(50))  # string because bvwp uses strings vor numbering projects, don't ask
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default=None)
    reason_project = db.Column(db.Text, default=None)
    bvwp_alternatives = db.Column(db.Text, default=None)
    effects_passenger_long_rail = db.Column(db.Boolean, default=False)
    effects_passenger_local_rail = db.Column(db.Boolean, default=False)
    effects_cargo_rail = db.Column(db.Boolean, default=False)

    #economical data
    nkv = db.Column(db.Float)
    length = db.Column(db.Float)
    priority = db.Column(db.String(100))
    reason_priority = db.Column(db.Text)

    # traffic forecast
    # # passenger
    relocation_car_to_rail = db.Column(db.Float)
    relocation_rail_to_car = db.Column(db.Float)
    relocation_air_to_rail = db.Column(db.Float)
    induced_traffic = db.Column(db.Float)
    delta_car_km = db.Column(db.Float)
    delta_km_rail = db.Column(db.Float)
    delta_rail_running_time = db.Column(db.Float)
    delta_rail_km_rail = db.Column(db.Float)
    delta_rail_km_car_to_rail = db.Column(db.Float)
    delta_rail_km_rail_to_car = db.Column(db.Float)
    delta_rail_km_air_to_rail = db.Column(db.Float)
    delta_rail_km_induced = db.Column(db.Float)
    delta_travel_time_rail = db.Column(db.Float)
    delta_travel_time_car_to_rail = db.Column(db.Float)
    delta_travel_time_rail_to_car = db.Column(db.Float)
    delta_travel_time_air_to_rail = db.Column(db.Float)
    delta_travel_time_induced = db.Column(db.Float)

    # # cargo
    relocation_truck_to_rail = db.Column(db.Float)
    relocation_ship_to_rail = db.Column(db.Float)
    delta_truck_km = db.Column(db.Float)
    delta_truck_count = db.Column(db.Float)
    delta_rail_cargo_count = db.Column(db.Float)
    delta_rail_cargo_running_time = db.Column(db.Float)
    delta_rail_cargo_km_lkw_to_rail = db.Column(db.Float)
    delta_rail_cargo_km_ship_to_rail = db.Column(db.Float)
    delta_rail_cargo_time_rail = db.Column(db.Float)
    delta_rail_cargo_time_lkw_to_rail = db.Column(db.Float)
    delta_rail_cargo_time_ship_to_rail = db.Column(db.Float)
    
    # use calculation
    # # passenger
    use_change_operation_cost_car_yearly = db.Column(db.Float)
    use_change_operating_cost_rail_yearly = db.Column(db.Float)
    use_change_operating_cost_air_yearly = db.Column(db.Float)
    use_change_pollution_car_yearly = db.Column(db.Float)
    use_change_pollution_rail_yearly = db.Column(db.Float)
    use_change_pollution_air_yearly = db.Column(db.Float)
    use_change_safety_car_yearly = db.Column(db.Float)
    use_change_safety_rail_yearly = db.Column(db.Float)
    use_change_travel_time_rail_yearly = db.Column(db.Float)
    use_change_travel_time_induced_yearly = db.Column(db.Float)
    use_change_travel_time_pkw_yearly = db.Column(db.Float)
    use_change_travel_time_air_yearly = db.Column(db.Float)
    use_change_travel_time_less_2min_yearly = db.Column(db.Float)
    use_change_implicit_benefit_induced_yearly = db.Column(db.Float)
    use_change_implicit_benefit_pkw_yearly = db.Column(db.Float)
    use_change_implicit_benefit_air_yearly = db.Column(db.Float)
    use_sum_passenger_yearly = db.Column(db.Float)

    use_change_operation_cost_car_present_value = db.Column(db.Float)
    use_change_operating_cost_rail_present_value = db.Column(db.Float)
    use_change_operating_cost_air_present_value = db.Column(db.Float)
    use_change_pollution_car_present_value = db.Column(db.Float)
    use_change_pollution_rail_present_value = db.Column(db.Float)
    use_change_pollution_air_present_value = db.Column(db.Float)
    use_change_safety_car_present_value = db.Column(db.Float)
    use_change_safety_rail_present_value = db.Column(db.Float)
    use_change_travel_time_rail_present_value = db.Column(db.Float)
    use_change_travel_time_induced_present_value = db.Column(db.Float)
    use_change_travel_time_pkw_present_value = db.Column(db.Float)
    use_change_travel_time_air_present_value = db.Column(db.Float)
    use_change_travel_time_less_2min_present_value = db.Column(db.Float)
    use_change_implicit_benefit_induced_present_value = db.Column(db.Float)
    use_change_implicit_benefit_pkw_present_value = db.Column(db.Float)
    use_change_implicit_benefit_air_present_value = db.Column(db.Float)
    use_sum_passenger_present_value = db.Column(db.Float)

    # # cargo
    use_change_operating_cost_truck_yearly = db.Column(db.Float)
    use_change_operating_cost_rail_cargo_yearly = db.Column(db.Float)
    use_change_operating_cost_ship_yearly = db.Column(db.Float)
    use_change_pollution_truck_yearly = db.Column(db.Float)
    use_change_pollution_rail_cargo_yearly = db.Column(db.Float)
    use_change_pollution_ship_yearly = db.Column(db.Float)
    use_change_safety_truck_yearly = db.Column(db.Float)
    use_change_safety_rail_cargo_yearly = db.Column(db.Float)
    use_change_safety_ship_yearly = db.Column(db.Float)
    use_change_running_time_rail_yearly = db.Column(db.Float)
    use_change_running_time_lkw_yearly = db.Column(db.Float)
    use_change_running_time_ship_yearly = db.Column(db.Float)
    use_change_implicit_benefit_truck_yearly = db.Column(db.Float)
    use_change_implicit_benefit_ship_yearly = db.Column(db.Float)
    use_change_reliability_yearly = db.Column(db.Float)
    use_sum_cargo_yearly = db.Column(db.Float)

    use_change_operating_cost_truck_present_value = db.Column(db.Float)
    use_change_operating_cost_rail_cargo_present_value = db.Column(db.Float)
    use_change_operating_cost_ship_present_value = db.Column(db.Float)
    use_change_pollution_truck_present_value = db.Column(db.Float)
    use_change_pollution_rail_cargo_present_value = db.Column(db.Float)
    use_change_pollution_ship_present_value = db.Column(db.Float)
    use_change_safety_truck_present_value = db.Column(db.Float)
    use_change_safety_rail_cargo_present_value = db.Column(db.Float)
    use_change_safety_ship_present_value = db.Column(db.Float)
    use_change_running_time_rail_present_value = db.Column(db.Float)
    use_change_running_time_lkw_present_value = db.Column(db.Float)
    use_change_running_time_ship_present_value = db.Column(db.Float)
    use_change_implicit_benefit_truck_present_value = db.Column(db.Float)
    use_change_implicit_benefit_ship_present_value = db.Column(db.Float)
    use_change_reliability_present_value = db.Column(db.Float)
    use_sum_cargo_present_value = db.Column(db.Float)

    # # other use
    use_change_maintenance_cost_yearly = db.Column(db.Float)
    use_change_lcc_infrastructure_yearly = db.Column(db.Float)
    use_change_noise_intown_yearly = db.Column(db.Float)
    use_change_noise_outtown_yearly = db.Column(db.Float)
    sum_use_change_yearly = db.Column(db.Float)

    use_change_maintenance_cost_present_value = db.Column(db.Float)
    use_change_lcc_infrastructure_present_value = db.Column(db.Float)
    use_change_noise_intown_present_value = db.Column(db.Float)
    use_change_noise_outtown_present_value = db.Column(db.Float)
    sum_use_change_present_value = db.Column(db.Float)

    # planning status
    ibn_planned = db.Column(db.Date)
    ibn_final = db.Column(db.Date)
    hoai = db.Column(db.Integer, nullable=False, default=0)
    parl_befassung_planned = db.Column(db.Boolean, nullable=False, default=False)
    parl_befassung_date = db.Column(db.Date)
    ro_finished = db.Column(db.Boolean, nullable=False, default=False)  # Raumordnung
    ro_finished_date = db.Column(db.Date)
    pf_finished = db.Column(db.Boolean, nullable=False, default=False)  # Planfeststellung fertiggestellt?
    pf_finished_date = db.Column(db.Date)
    bvwp_duration_of_outstanding_planning = db.Column(db.Float)
    bvwp_duration_of_build = db.Column(db.Float)
    bvwp_duration_operating = db.Column(db.Float)

    # properties of project
    nbs = db.Column(db.Boolean, nullable=False, default=False)
    abs = db.Column(db.Boolean, nullable=False, default=False)
    elektrification = db.Column(db.Boolean, nullable=False, default=False)
    batterie = db.Column(db.Boolean, nullable=False, default=False)
    second_track = db.Column(db.Boolean, nullable=False, default=False)
    third_track = db.Column(db.Boolean, nullable=False, default=False)
    fourth_track = db.Column(db.Boolean, nullable=False, default=False)
    curve = db.Column(db.Boolean, nullable=False, default=False)  # Neue Verbindungskurve
    platform = db.Column(db.Boolean, nullable=False, default=False)  # Neuer Bahnsteig
    junction_station = db.Column(db.Boolean, nullable=False, default=False)
    number_junction_station = db.Column(db.Integer)  # TODO: Set it minimum 1 if junction_station is true
    overtaking_station = db.Column(db.Boolean, nullable=False, default=False)
    number_overtaking_station = db.Column(db.Integer)  # TODO: Set it minimum 1 if junction_station is true
    double_occupancy = db.Column(db.Boolean, nullable=False, default=False)
    block_increase = db.Column(db.Boolean, nullable=False, default=False)
    flying_junction = db.Column(db.Boolean, nullable=False, default=False)
    tunnel_structural_gauge = db.Column(db.Boolean, nullable=False, default=False)
    increase_speed = db.Column(db.Boolean, nullable=False, default=False)
    new_vmax = db.Column(db.Integer)
    level_free_platform_entrance = db.Column(db.Boolean, nullable=False, default=False)
    etcs = db.Column(db.Boolean, nullable=False, default=False)
    etcs_level = db.Column(db.Integer)

    # environmental data
    bvwp_environmental_impact = db.Column(db.String(200))
    delta_nox = db.Column(db.Float)
    delta_co = db.Column(db.Float)
    delta_co2 = db.Column(db.Float)
    delta_hc = db.Column(db.Float)
    delta_pm = db.Column(db.Float)
    delta_so2 = db.Column(db.Float)

    bvwp_sum_use_environment = db.Column(db.Float)
    bvwp_sum_environmental_affectedness = db.Column(db.String(255))
    bvwp_sum_environmental_affectedness_text = db.Column(db.Text)
    noise_new_affected = db.Column(db.Float)
    noise_relieved = db.Column(db.Float)
    change_noise_outtown = db.Column(db.Float)

    area_nature_high_importance = db.Column(db.Float)
    area_nature_high_importance_per_km = db.Column(db.Float)
    area_nature_high_importance_rating = db.Column(db.String(255))
    natura2000_rating = db.Column(db.String(255))
    natura2000_not_excluded =  db.Column(db.Float)
    natura2000_probably =  db.Column(db.Float)
    ufr_250 = db.Column(db.Float)
    ufr_250_per_km = db.Column(db.Float)
    ufra_250_rating = db.Column(db.String(255))
    bfn_rating = db.Column(db.String(255))
    ufr_1000_undissacted_large_area = db.Column(db.Float)
    ufr_1000_undissacted_large_area_per_km = db.Column(db.Float)
    ufr_1000_undissacted_large_mammals = db.Column(db.Float)
    ufr_1000_undissacted_large_mammals_per_km = db.Column(db.Float)
    count_undissacted_area = db.Column(db.Float)
    count_reconnect_area = db.Column(db.Float)
    land_consumption = db.Column(db.Float)
    flooding_area = db.Column(db.Float)
    flooding_area_per_km = db.Column(db.Float)
    flooding_area_rating = db.Column(db.String(255))
    water_protection_area = db.Column(db.Float)
    water_protection_area_per_km = db.Column(db.Float)
    water_protection_area_rating = db.Column(db.String(255))
    uzvr = db.Column(db.Float)
    uvzr_rating = db.Column(db.String(255))
    priortiy_area_landscape_protection = db.Column(db.Float)
    priority_area_landscape_protection_per_km = db.Column(db.Float)
    priority_area_landscape_protection_rating = db.Column(db.String(255))
    environmental_additional_informations = db.Column(db.Text)

    # financial data
    lfd_nr = db.Column(db.Integer)
    finve_nr = db.Column(db.Integer)
    bedarfsplan_nr = db.Column(db.Integer)
    planned_total_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Integer)
    bvwp_planned_cost = db.Column(db.Float)
    bvwp_planned_maintenance_cost = db.Column(db.Float)
    bvwp_planned_planning_cost = db.Column(db.Float)
    bvwp_planned_planning_cost_incurred = db.Column(db.Float)
    bvwp_total_budget_relevant_cost = db.Column(db.Float)
    bvwp_total_budget_relevant_cost_incurred = db.Column(db.Float)
    bvwp_valuation_relevant_cost = db.Column(db.Float)
    bvwp_valuation_relevant_cost_pricelevel_2012 = db.Column(db.Float)

    bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost = db.Column(db.Float)
    bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cost = db.Column(db.Float)
    bvwp_valuation_relevant_cost_pricelevel_2012_present_value = db.Column(db.Float)

    # spatial significance
    bvwp_regional_significance = db.Column(db.String(255))
    spatial_significance_overall_result = db.Column(db.Text)
    spatial_significance_reasons = db.Column(db.Text)
    spatial_significance_street = db.Column(db.Text)
    spatial_significance_accessibility_deficits = db.Column(db.Text)
    spatial_significance_conclusion = db.Column(db.Text)

    # capacity
    bottleneck_elimination = db.Column(db.Boolean)
    bvwp_congested_rail_reference_6to9_km = db.Column(db.Float)
    bvwp_congested_rail_reference_6to9_perc = db.Column(db.Float)
    bvwp_congested_rail_plancase_6to9_km = db.Column(db.Float)
    bvwp_congested_rail_plancase_6to9_perc = db.Column(db.Float)

    bvwp_congested_rail_reference_9to16_km = db.Column(db.Float)
    bvwp_congested_rail_reference_9to16_perc = db.Column(db.Float)
    bvwp_congested_rail_plancase_9to16_km = db.Column(db.Float)
    bvwp_congested_rail_plancase_9to16_perc = db.Column(db.Float)

    bvwp_congested_rail_reference_16to19_km = db.Column(db.Float)
    bvwp_congested_rail_reference_16to19_perc = db.Column(db.Float)
    bvwp_congested_rail_plancase_16to19_km = db.Column(db.Float)
    bvwp_congested_rail_plancase_16to19_perc = db.Column(db.Float)

    bvwp_congested_rail_reference_19to22_km = db.Column(db.Float)
    bvwp_congested_rail_reference_19to22_perc = db.Column(db.Float)
    bvwp_congested_rail_plancase_19to22_km = db.Column(db.Float)
    bvwp_congested_rail_plancase_19to22_perc = db.Column(db.Float)

    bvwp_congested_rail_reference_22to6_km = db.Column(db.Float)
    bvwp_congested_rail_reference_22to6_perc = db.Column(db.Float)
    bvwp_congested_rail_plancase_22to6_km = db.Column(db.Float)
    bvwp_congested_rail_plancase_22to6_perc = db.Column(db.Float)

    bvwp_congested_rail_reference_day_km = db.Column(db.Float)
    bvwp_congested_rail_reference_day_perc = db.Column(db.Float)
    bvwp_congested_rail_plancase_day_km = db.Column(db.Float)
    bvwp_congested_rail_plancase_day_perc = db.Column(db.Float)

    bvwp_unscheduled_waiting_period_reference = db.Column(db.Float)
    bvwp_unscheduled_waiting_period_plancase = db.Column(db.Float)

    bvwp_punctuality_cargo_reference = db.Column(db.Float)
    bvwp_delta_punctuality_relativ = db.Column(db.Float)
    bvwp_delta_punctuality_absolut = db.Column(db.Float)

    # travel time
    traveltime_reduction = db.Column(db.Float)
    bvwp_traveltime_examples = db.Column(db.String)

    # additional informations
    bvwp_additional_informations = db.Column(db.Text)

    # references
    budgets = db.relationship('Budget', backref='project_content', lazy=True)
    texts = db.relationship('Text', secondary=texts_to_project_content,
                            backref=db.backref('project_content', lazy=True))
    projectcontent_groups = db.relationship('ProjectGroup', secondary=projectcontent_to_group,
                                            backref=db.backref('projects_content', lazy=True))
    projectcontent_railway_lines = db.relationship('RailwayLine', secondary=projectcontent_to_line,
                                                   backref=db.backref('project_content', lazy=True))
    states = db.relationship("States", secondary=project_contents_to_states,
                                            backref=db.backref('states', lazy=True))
    counties = db.relationship("Counties", secondary=project_contents_to_counties,
                               backref=db.backref('counties', lazy=True))

    constituencies = db.relationship("Constituencies", secondary=project_contents_to_constituencies,
                                     backref = db.backref('constituencies', lazy=True))


class ProjectGroup(db.Model):
    __tablename__ = 'project_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)


class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    project_content_id = db.Column(db.Integer, db.ForeignKey('projects_contents.id'))
    name = db.Column(db.String(100))
    type = db.Column(db.String(100))  # TODO: ENUM: FinVe, Bedarfsplan, etc.
    year = db.Column(db.Integer)
    spent_cost_two_years_before = db.Column(db.Integer)
    allowed_year_before = db.Column(db.Integer)
    delegated_costs = db.Column(db.Integer)
    planned_cost_this_year = db.Column(db.Integer)
    planned_cost_next_year = db.Column(db.Integer)
    planned_cost_following_years = db.Column(db.Integer)


class Text(db.Model):
    __tablename__ = 'texts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    type = db.Column(db.Integer, db.ForeignKey('text_types.id'))

    # relationship
    text_type = db.relationship('TextType', backref='text_types', lazy=True)


class TextType(db.Model):
    __tablename__ = 'text_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))


class States(db.Model):
    """
    states (Bundesländer)
    """
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    name_short_2 = db.Column(db.String, nullable=False)
    polygon = db.Column(geoalchemy2.Geometry(geometry_type='POLYGON', srid=4326), nullable=True)


class Counties(db.Model):
    """
    Counties (Kreis)
    """
    __tablenmae__= 'counties'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)
    name_short = db.Column(db.String(255), nullable=False)
    polygon = db.Column(geoalchemy2.Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey('states.id'))


class Constituencies(db.Model):
    """
    Constituencies
    """
    __tablename__= 'constituencies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    polygon = db.Column(geoalchemy2.Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey('states.id'))


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    registered_on = db.Column(db.DateTime, nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, username, email, password, admin=False):
        self.username = username
        self.email = email
        self.password = bcrypt.generate_password_hash(
            password, app.config.get('BCRYPT_LOG_ROUNDS')
        ).decode()
        self.registered_on = datetime.datetime.now()
        self.admin = admin

    def encode_auth_token(self, user_id):
        """
        Generates the Auth Token
        :param user_id:
        :return: string
        """
        try:
            payload = {
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=0, minutes=60),
                "iat": datetime.datetime.utcnow(),
                "sub": user_id
            }
            return jwt.encode(
                payload,
                app.config.get('SECRET_KEY'),
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer | string
        """
        try:
            payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'), algorithms=['HS256'])
            is_blacklisted_token = BlacklistToken.check_blacklist(auth_token)
            if is_blacklisted_token:
                return 'Token blacklisted. Please log in again.'
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'

    @staticmethod
    def verify_auth_token(token):
        pass


class BlacklistToken(db.Model):
    """
    Token Model for storing JWT Tokens
    """
    __tablename__ = 'blacklist_tokens'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = datetime.datetime.now()

    def __repr__(self):
        return "<id: token: {}".format(self.token)

    @staticmethod
    def check_blacklist(auth_token):
        # check whether auth token has been blacklisted
        res = BlacklistToken.query.filter_by(token=str(auth_token)).first()
        if res:
            return True
        else:
            return False
