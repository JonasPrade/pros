import datetime
import jwt
import geojson
import geoalchemy2
import shapely
import sqlalchemy
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.associationproxy import association_proxy
import math
import logging

from prosd import db, app, bcrypt

START_DATE = datetime.datetime(2030, 1, 1)

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
                            db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id', onupdate='CASCADE', ondelete='CASCADE')),
                            db.Column('projectgroup_id', db.Integer, db.ForeignKey('project_groups.id', onupdate='CASCADE', ondelete='CASCADE'))
                            )

# project to railway Lines
projectcontent_to_line = db.Table('projectcontent_to_lines',
                           db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id')),
                           db.Column('railway_lines_id', db.Integer, db.ForeignKey('railway_lines.id'))
                           )


projectcontent_to_railwaystations = db.Table('projectcontent_to_railwaystations',
                                       db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                       db.Column('railway_station_id', db.Integer, db.ForeignKey('railway_stations.id'))

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
                           db.Column('node_id', db.Integer, db.ForeignKey('railway_nodes.id', ondelete='CASCADE')),
                           db.Column('route_id', db.Integer, db.ForeignKey('railway_route.id'))
                           )

formations_to_vehicles = db.Table('formations_to_vehicles',
                                  db.Column('formation_id', db.String(100), db.ForeignKey('formations.id')),
                                  db.Column('vehicle_id', db.String(100), db.ForeignKey('vehicles.id'))
                                  )

traingroup_to_railwaylines = db.Table('traingroup_to_railwaylines',
                                      db.Column('traingroup_id', db.String(255), db.ForeignKey('timetable_train_groups.id')),
                                      db.Column('railway_lines_id', db.Integer, db.ForeignKey('railway_lines.id'))
                                      )

finve_to_projectcontent = db.Table('finve_to_projectcontent',
                                    db.Column('finve_id', db.Integer, db.ForeignKey('finve.id')),
                                    db.Column('pc_id', db.Integer, db.ForeignKey('projects_contents.id'))
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
    catenary = db.Column(db.Boolean, default=False)
    conductor_rail = db.Column(db.Boolean, default=False)
    voltage = db.Column(db.Float, default=None)
    dc_ac = db.Column(db.String(3), default=None)
    number_tracks = db.Column(db.String(100))  # eingleisig, zweigleisig
    vmax = db.Column(db.String(20))
    type_of_transport = db.Column(db.String(20))  # Pz-Bahn, Gz- Bahn, Pz/Gz-Bahn, S-Bahn, Hafenbahn, Seilzugbahn
    strecke_kuerzel = db.Column(db.String(100))
    bahnart = db.Column(db.String(100))
    active_until = db.Column(db.Integer)
    active_since = db.Column(db.Integer)
    coordinates = db.Column(geoalchemy2.Geometry(geometry_type='LINESTRING', srid=4326), nullable=False)
    railway_infrastructure_company = db.Column(db.Integer, db.ForeignKey('railway_infrastructure_company.id', ondelete='SET NULL'))
    abs_nbs = db.Column(db.String(5), default='KS')
    gauge = db.Column(db.Integer, default=1435)

    # manipulate_geodata_and_db
    start_node = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', ondelete='SET NULL'))
    end_node = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', ondelete='SET NULL'))

    def __init__(self, coordinates, route_number=None, direction=0, length=None, from_km=None, to_km=None, electrified=None,
                 catenary = False, conductor_rail = False, voltage = None, dc_ac = None,
                 number_tracks=None, vmax=None, type_of_transport=None, bahnart=None,
                 strecke_kuerzel=None, active_until=None, active_since=None, railway_infrastructure_company=None, gauge=1435, abs_nbs='ks'):
        self.route_number = route_number
        self.direction = direction
        self.length = length
        self.from_km = from_km
        self.to_km = to_km
        self.electrified = electrified
        self.catenary = catenary
        self.conductor_rail = conductor_rail
        self.voltage = voltage
        self.dc_ac = dc_ac
        self.number_tracks = number_tracks
        self.vmax = vmax
        self.type_of_transport = type_of_transport
        self.strecke_kuerzel = strecke_kuerzel
        self.bahnart = bahnart
        self.active_until = active_until
        self.active_since = active_since
        self.coordinates = coordinates
        self.railway_infrastructure_company = railway_infrastructure_company
        self.abs_nbs = abs_nbs
        self.gauge = gauge

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
        # TODO: Transfer also project_content
        if isinstance(coordinates, str):
            coordinates = coordinates.split(",")[1][:-1]
            coordinates_wkb = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_Force2D(coordinates))).one()[0]
        else:
            coordinates_wkb = coordinates

        railline = RailwayLine(
            coordinates=coordinates_wkb,
            route_number=line_old.route_number,
            direction=line_old.direction,
            from_km=line_old.from_km,
            to_km=line_old.to_km,
            electrified=line_old.electrified,
            catenary=line_old.catenary,
            conductor_rail=line_old.conductor_rail,
            voltage=line_old.voltage,
            dc_ac=line_old.dc_ac,
            number_tracks=line_old.number_tracks,
            vmax=line_old.vmax,
            type_of_transport=line_old.type_of_transport,
            bahnart=line_old.bahnart,
            strecke_kuerzel=line_old.strecke_kuerzel,
            active_until=line_old.active_until,
            active_since=line_old.active_since,
            railway_infrastructure_company=line_old.railway_infrastructure_company,
        )

        railline.project_content = line_old.project_content

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
    db_kuerzel = db.Column(db.String(6))
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
    db_kuerzel = db.Column(db.String(6), unique=True)
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
    keeps all nodes for the railway network to create a network manipulate_geodata_and_db
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
        :param node_id:
        :param route_number:
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
    superior_project_content_id = db.Column(db.Integer, db.ForeignKey('projects_contents.id'))  # TODO: Change that to project_content

    # references
    project_contents = db.relationship('ProjectContent', backref='project', lazy=True, foreign_keys="ProjectContent.project_id")
    superior_project = db.relationship("ProjectContent", backref='sub_project', foreign_keys=[superior_project_content_id])

    def __init__(self, name, description='', superior_project_id=None):
        self.name = name
        self.description = description
        self.superior_project = superior_project_id


class ProjectContent(db.Model):
    __tablename__ = 'projects_contents'

    # Basic informations
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    project_number = db.Column(db.String(50))  # string because calculation_methods uses strings vor numbering projects, don't ask
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
    station_railroad_switches = db.Column(db.Boolean, default=False)
    new_station = db.Column(db.Boolean, default=False)
    depot = db.Column(db.Boolean, default=False)

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
    bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos = db.Column(db.Float)
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

    # calculation of operating cost
    # #  spfv
    use_capital_service_spfv = db.Column(db.Float)
    use_maintenance_cost_spfv = db.Column(db.Float)
    use_energy_cost_spfv = db.Column(db.Float)
    # # spnv
    use_capital_service_spnv = db.Column(db.Float)
    use_maintenance_cost_spnv = db.Column(db.Float)
    use_energy_cost_spnv = db.Column(db.Float)
    # # sgv
    use_capital_service_loco_sgv = db.Column(db.Float)
    use_maintenance_cost_loco_sgv = db.Column(db.Float)
    use_energy_cost_sgv = db.Column(db.Float)
    use_change_traction_sgv = db.Column(db.Float)

    # references
    # project = db.relationship("Project", backref='project_contents', lazy=True, foreign_keys=[project_id])
    texts = db.relationship('Text', secondary=texts_to_project_content,
                            backref=db.backref('project_content', lazy=True))
    projectcontent_groups = db.relationship('ProjectGroup', secondary=projectcontent_to_group,
                                            backref=db.backref('projects_content', lazy=True))
    projectcontent_railway_lines = db.relationship('RailwayLine', secondary=projectcontent_to_line,
                                                   backref=db.backref('project_content', lazy=True))
    railway_stations = db.relationship('RailwayStation', secondary=projectcontent_to_railwaystations,
                                       backref=db.backref('project_content', lazy=True))
    states = db.relationship("States", secondary=project_contents_to_states,
                                            backref=db.backref('states', lazy=True))
    counties = db.relationship("Counties", secondary=project_contents_to_counties,
                               backref=db.backref('counties', lazy=True))
    constituencies = db.relationship("Constituencies", secondary=project_contents_to_constituencies,
                                     backref = db.backref('constituencies', lazy=True))

    @classmethod
    def add_lines_to_pc(self, pc_id, lines):
        """
        adds list of lines to pc
        :param pc_id:
        :param lines:
        :return:
        """
        pc = ProjectContent.query.get(pc_id)
        for line_id in lines:
            line = RailwayLine.query.get(line_id)
            pc.projectcontent_railway_lines.append(line)

        db.session.add(pc)
        db.session.commit()


class ProjectGroup(db.Model):
    __tablename__ = 'project_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)

    @hybrid_property
    def projects(self):
        projects_id = set()
        for pc in self.projects_content:
            projects_id.add(pc.project)

        return projects_id

    @hybrid_property
    def superior_projects(self):
        # all projects that do not have an superior Project
        projects_id = set()
        for pc in self.projects_content:
            if pc.project.superior_project_content_id is None:
                projects_id.add(pc.project)

        return projects_id


class Vehicle(db.Model):
    """
    vehicles
    """
    __tablename__ = 'vehicles'
    id = db.Column(db.String(100), primary_key=True)
    code = db.Column(db.String(100))
    name = db.Column(db.String(100))
    length = db.Column(db.Float)
    speed = db.Column(db.Integer)
    brutto_weight = db.Column(db.Float)
    engine = db.Column(db.Boolean)
    wagon = db.Column(db.Boolean)

    vehicle_pattern_id = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))

    vehicle_pattern = db.relationship("VehiclePattern", backref="vehicles")

    @classmethod
    def get_vehicle_use(self, vehicle):
        formations = vehicle.formations
        train_information = []
        for formation in formations:
            train_part = formation.train_part[0]
            info = dict()
            info["category"] = train_part.category.description
            info["timetable_group"] = train_part.train[0].train_group.code
            info["start"] = train_part.first_ocp.ocp.name
            info["end"] = train_part.last_ocp.ocp.name
            info["length"] = train_part.train[0].train_group.length_line

        return train_information


class VehiclePattern(db.Model):
    """
    patterns for vehicles that have more informations about energy usage etc.
    """
    __tablename__ = 'vehicles_pattern'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type_of_traction = db.Column(db.String(255), nullable=False)
    wagons_of_trainset = db.Column(db.Integer)
    seats = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    traction = db.Column(db.Integer)
    speed_max = db.Column(db.Integer)
    tilting = db.Column(db.Boolean, default=False)
    couple_allowed = db.Column(db.Boolean, default=True)
    length = db.Column(db.Integer)
    investment_cost = db.Column(db.Float)
    investment_cost_standi = db.Column(db.Float)
    debt_service = db.Column(db.Float)
    vehicle_cost_km = db.Column(db.Float)
    maintenance_cost_km = db.Column(db.Float, comment="per vehicle-km")
    maintenance_cost_year = db.Column(db.Float, comment="maintenance cost calculated by duration")
    maintenance_cost_length_t = db.Column(db.Float, comment="€/1000tkm")
    maintenance_cost_duration_t = db.Column(db.Float, comment="€/(t*year)")
    train_driver_cost = db.Column(db.Float, comment="per vehicle-hour")
    head_of_train_cost = db.Column(db.Float, comment="per vehicle-hour")
    energy_per_km = db.Column(db.Float, comment="kWh/vehicle-km")
    energy_per_tkm = db.Column(db.Float, comment="energy_unit/1000tkm")
    energy_abs_per_km = db.Column(db.Float)
    energy_nbs_per_km = db.Column(db.Float)
    energy_cost_per_km = db.Column(db.Float)
    energy_cost_stop = db.Column(db.Float)
    fuel_consumption_diesel_km = db.Column(db.Float)
    fuel_consumption_h2_km = db.Column(db.Float)
    energy_consumption_hour = db.Column(db.Float)
    fuel_consumption_diesel_hour = db.Column(db.Float)
    fuel_consumption_h2_hour = db.Column(db.Float)
    energy_stop_a = db.Column(db.Float)
    energy_stop_b = db.Column(db.Float)
    emission_production_vehicle = db.Column(db.Float, comment="kg CO2/Leermasse * Jahr")
    emission_production_vehicle_calc = db.Column(db.Float, comment="t CO2/(Fahrzeug * Jahr)")
    additional_energy_without_overhead = db.Column(db.Float)
    additional_maintenance_cost_withou_overhead = db.Column(db.Float)
    co2_km = db.Column(db.Float, comment="g/km")
    co2_stop = db.Column(db.Float, comment="g/stop")
    emission_km = db.Column(db.Float, comment="€/km")
    emission_stop = db.Column(db.Float, comment="€/stop")
    project_group = db.Column(db.Integer, db.ForeignKey('project_groups.id'))


class Formation(db.Model):
    """
    Formations of vehicles
    """
    __tablename__ = 'formations'
    id = db.Column(db.String(100), primary_key=True)
    description = db.Column(db.String(100))
    length = db.Column(db.Float)
    speed = db.Column(db.Integer)
    weight = db.Column(db.Float)

    vehicles = db.relationship("Vehicle", secondary=formations_to_vehicles, backref="formations")

    @hybrid_property
    def maintenance_cost_km(self):
        maintenance_cost_km = 0
        for vehicle in self.vehicles:
            maintenance_cost_km += vehicle.vehicle_pattern.maintenance_cost_km
        return maintenance_cost_km

    @hybrid_property
    def weight(self):
        weight = 0
        for vehicle in self.vehicles:
            weight += vehicle.vehicle_pattern.weight
        return weight

    @hybrid_property
    def type_of_traction(self):
        type_of_traction = self.vehicles[0].vehicle_pattern.type_of_traction
        return type_of_traction

    @hybrid_property
    def energy_stop_a(self):
        energy_stop_a = self.vehicles[0].vehicle_pattern.energy_stop_a
        return energy_stop_a

    @hybrid_property
    def energy_stop_b(self):
        energy_stop_b = self.vehicles[0].vehicle_pattern.energy_stop_b
        return energy_stop_b

    @hybrid_property
    def additional_energy_without_overhead(self):
        additional_energy_without_overhead = self.vehicles[0].vehicle_pattern.additional_energy_without_overhead
        return additional_energy_without_overhead

    @hybrid_property
    def additional_maintenance_cost_without_overhead(self):
        additional_maintenance_cost_without_overhead = self.vehicles[0].vehicle_pattern.additional_maintenance_cost_withou_overhead
        return additional_maintenance_cost_without_overhead

    @hybrid_property
    def energy_per_km(self):
        energy_per_km = 0
        for vehicle in self.vehicles:
            energy_per_km += vehicle.vehicle_pattern.energy_per_km
        return energy_per_km

    @hybrid_property
    def seats(self):
        seats = 0
        for vehicle in self.vehicles:
            seats += vehicle.vehicle_pattern.seats
        return seats


class TimetablePeriod(db.Model):
    """
    Periods of timetable that is loaded to the db
    """
    __tablename__ = 'timetable_period'
    id = db.Column(db.String(15), primary_key=True)
    name = db.Column(db.String(255))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)


class TimetableOperatingPeriod(db.Model):
    __tablename__ = 'timetable_operating_period'
    id = db.Column(db.String(31), primary_key=True)
    code = db.Column(db.String(255))
    timetablePeriodRef = db.Column(db.String(15), db.ForeignKey('timetable_period.id', ondelete='SET NULL'))
    startDate = db.Column(db.Date)
    endDate = db.Column(db.Date)


class TimetableCategory(db.Model):
    __tablename__ = 'timetable_categories'
    id = db.Column(db.String(15), primary_key=True)
    code = db.Column(db.String(255))
    description = db.Column(db.String(255))
    transport_mode = db.Column(db.String(5))

    train_part = db.relationship("TimetableTrainPart", lazy=True, backref="category")


class TimetableTrainGroup(db.Model):
    __tablename__ = 'timetable_train_groups'

    def __repr__(self):
        return f"TrainGroup {self.code} {self.description}"

    id = db.Column(db.String(255), primary_key=True)
    code = db.Column(db.String(255))
    train_number = db.Column(db.Integer)
    traingroup_line = db.Column(db.String(255), db.ForeignKey('timetable_lines.code', ondelete='SET NULL', onupdate='CASCADE'))

    trains = db.relationship("TimetableTrain", lazy=True, backref="train_group")
    traingroup_lines = db.relationship("TimetableLine", lazy=True, backref="train_groups")
    lines = db.relationship("RailwayLine", secondary=traingroup_to_railwaylines, backref="train_groups")

    @hybrid_property
    def length_line(self):
        km = 0
        for line in self.lines:
            km += line.length/1000

        return km

    @hybrid_property
    def running_km_day(self):
        running_km_day = self.length_line * len(self.trains)

        return running_km_day

    @hybrid_property
    def running_km_day_abs(self):
        running_km_day_abs = 0
        for line in self.lines:
            if line.abs_nbs == "ABS":
                running_km_day_abs += line.length/1000

        running_km_day_abs = running_km_day_abs * len(self.trains)
        return running_km_day_abs

    @hybrid_property
    def running_km_day_nbs(self):
        running_km_day_nbs = 0
        for line in self.lines:
            if line.abs_nbs == "NBS":
                running_km_day_nbs += line.length/1000

        running_km_day_nbs = running_km_day_nbs * len(self.trains)
        return running_km_day_nbs

    @hybrid_property
    def running_km_day_no_catenary(self):
        running_km_day_no_catenary = 0
        for line in self.lines:
            if line.catenary == False:
                running_km_day_no_catenary += line.length/1000

        running_km_day_no_catenary = running_km_day_no_catenary * len(self.trains)
        return running_km_day_no_catenary

    @hybrid_property
    def running_km_year(self):
        running_km_year = self.running_km_day * 365 / 1000
        return running_km_year

    @hybrid_property
    def running_km_year_abs(self):
        running_km_year_abs = self.running_km_day_abs * 365 / 1000
        return running_km_year_abs

    @hybrid_property
    def running_km_year_nbs(self):
        running_km_year_nbs = self.running_km_day_nbs * 365 / 1000
        return running_km_year_nbs

    @hybrid_property
    def running_km_year_no_catenary(self):
        running_km_year_no_catenary = self.running_km_day_no_catenary * 365 / 1000
        return running_km_year_no_catenary

    @hybrid_property
    def minimal_run_time(self):
        #TODO: There are sections with no run time. Check whats the problem
        train = self.trains[0]
        ocps = train.train_part.timetable_ocps
        minimal_run_time = datetime.timedelta(seconds=0)

        for ocp in ocps:
            sections = ocp.section
            for section in sections:
                section_time = section.minimal_run_time
                if section_time:
                    timedelta = datetime.timedelta(hours=section_time.hour, minutes=section_time.minute, seconds = section_time.second)
                    minimal_run_time += timedelta
        return minimal_run_time

    @hybrid_property
    def travel_time(self):
        train = self.trains[0]
        departure_first_time = train.train_part.first_ocp.times.filter(TimetableTime.scope == "scheduled").one().departure
        arrival_last_time = train.train_part.last_ocp.times.filter(TimetableTime.scope == "scheduled").one().arrival
        departure_first = datetime.datetime.combine(datetime.date.today(), departure_first_time)
        arrival_last = datetime.datetime.combine(datetime.date.today(), arrival_last_time)
        #TODO: Check for arrival after midnight
        travel_time = arrival_last - departure_first

        return travel_time

    @hybrid_property
    def running_time_day(self):
        running_time_day = self.travel_time * len(self.trains)

        return running_time_day

    @hybrid_property
    def running_time_year(self):
        """
        Tsd. Zug/std per year
        :return:
        """
        running_time_year = self.running_time_day * 365
        running_time_year = (running_time_year.days*24 + running_time_year.seconds/3600)/1000
        # running_time_year = running_time_year.seconds/3600
        return running_time_year

    @hybrid_property
    def stops_count(self):
        """
        count of stops (with passenger exchange for passenger trains)
        :return:
        """
        count_stops = 0
        train = self.trains[0]
        ocps = train.train_part.timetable_ocps

        for ocp in ocps:
            if ocp.ocp_type == 'stop':
                count_stops += 1

        return count_stops

    @hybrid_property
    def stops_count_year(self):
        """
        count of stops in a year
        :return:
        """
        count_stops_year = self.stops_count * len(self.trains) * 365
        return count_stops_year

    @hybrid_property
    def stops(self):
        """
        list of stops
        :return:
        """
        stops = []
        train = self.trains[0]
        ocps = train.train_part.timetable_ocps

        for ocp in ocps:
            if ocp.ocp_type == 'stop':
                stops.append(ocp.ocp)

        return stops

    @hybrid_property
    def stops_duration(self):
        """
        summed duration of all stops in one direction
        :return:
        """
        stops_duration = datetime.timedelta(seconds=0)
        train = self.trains[0]
        ocps = train.train_part.timetable_ocps

        for ocp in ocps:
            if ocp.ocp_type == 'stop':
                for time in ocp.times.all():
                    if time.scope == 'scheduled' and (time.arrival is not None and time.departure is not None):
                        stop_duration = datetime.datetime.combine(datetime.date.min, time.departure) - datetime.datetime.combine(datetime.date.min, time.arrival)
                        stops_duration += stop_duration

        return stops_duration

    @hybrid_property
    def stops_duration_average(self):
        """
        average of the duration of a stop (first and last stop is ignored)
        :return:
        """
        stops_duration_average = (self.stops_duration/(self.stops_count-2))
        return stops_duration_average


    @hybrid_property
    def vehicles(self):
        train = self.trains[0]  # all trains have same formation (checked)
        vehicles = train.train_part.formation.vehicles

        return vehicles

    @hybrid_property
    def description(self):
        description = self.trains[0].description
        return description

    @hybrid_property
    def first_ocp(self):
        first_ocp = self.trains[0].train_part.first_ocp
        return first_ocp

    @hybrid_property
    def last_ocp(self):
        last_ocp = self.trains[0].train_part.last_ocp
        return last_ocp

    @hybrid_property
    def category(self):
        category = self.trains[0].train_part.category
        return category


class TimetableTrain(db.Model):

    def __repr__(self):
        return f"TimetableTrain {self.id} {self.train_part}"

    __tablename__ = 'timetable_train'
    id = db.Column(db.String(510), primary_key=True)
    description = db.Column(db.Text)
    type = db.Column(db.String(255))
    train_number = db.Column(db.String(255))
    train_group_id = db.Column(db.String(255), db.ForeignKey('timetable_train_groups.id'))
    train_group_sequence = db.Column(db.String(255))
    line_number = db.Column(db.String(255))
    train_validity_name = db.Column(db.String(255))
    train_part_id = db.Column(db.String(510), db.ForeignKey('timetable_train_parts.id'))
    speed_profile_ref = db.Column(db.String(255))
    brake_type = db.Column(db.String(255))
    air_brake_application_position = db.Column(db.String(255))
    regular_brake_percentage = db.Column(db.Integer)

    train_part = db.relationship("TimetableTrainPart", backref="train", lazy=True)


class TimetableTrainPart(db.Model):
    __tablename__ = 'timetable_train_parts'

    def __repr__(self):
        return f"TimetableTrain {self.id} {self.first_ocp.ocp.code} {self.first_ocp_departure} {self.last_ocp.ocp.code} {self.last_ocp_arrival}"

    id = db.Column(db.String(510), primary_key=True)
    category_id = db.Column(db.String(15), db.ForeignKey('timetable_categories.id'))
    formation_id = db.Column(db.String(100), db.ForeignKey('formations.id'))
    operating_period_id = db.Column(db.String(31), db.ForeignKey('timetable_operating_period.id'))

    timetable_ocps = db.relationship("TimetableOcp", lazy=True, order_by="asc(TimetableOcp.sequence)")
    formation = db.relationship("Formation", lazy=True, backref="train_part")

    @hybrid_property
    def first_ocp(self):
        first_ocp = self.timetable_ocps[0]
        return first_ocp

    @first_ocp.expression
    def first_ocp(cls):
        statement = sqlalchemy.select(TimetableOcp)
        statement = statement.where(TimetableOcp.train_part == cls.id)
        statement = statement.order_by(TimetableOcp.sequence)
        statement = statement.limit(1)
        # sqlalchemy.select([TimetableTrainPart.timetable_ocps]).where(TimetableOcp.train_part == cls.id).order_by(TimetableOcp.sequence).limit(1)
        return statement

    @hybrid_property
    def last_ocp(self):
        last_ocp = self.timetable_ocps[-1]
        return last_ocp

    @last_ocp.expression
    def last_ocp(cls):
        statement = sqlalchemy.select(TimetableOcp)
        statement = statement.where(TimetableOcp.train_part == cls.id)
        statement = statement.order_by(sqlalchemy.desc(TimetableOcp.sequence))
        statement = statement.limit(1)
        #sqlalchemy.select([TimetableTrainPart.timetable_ocps]).where(TimetableOcp.train_part == cls.id).order_by(TimetableOcp.sequence).limit(1)
        return statement

    @hybrid_property
    def first_ocp_departure(self):
        first_ocp_departure = None
        for time in self.first_ocp.times.all():
            if time.scope == 'scheduled':
                first_ocp_departure = time.departure_with_day
                break

        return first_ocp_departure

    @property
    def last_ocp_arrival(self):
        last_ocp_arrival = None
        for time in self.last_ocp.times.all():
            if time.scope == 'scheduled':
                last_ocp_arrival = time.arrival_with_day
                break

        return last_ocp_arrival


class TimetableOcp(db.Model):
    __tablename__ = 'timetable_ocps'

    def __repr__(self):
        return f"TimetableOcp {self.ocp.code} {self.ocp_type} {self.scheduled_time} {self.section}"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    train_part = db.Column(db.String(510), db.ForeignKey('timetable_train_parts.id'))
    sequence = db.Column(db.Integer)
    ocp_id = db.Column(db.String(255), db.ForeignKey('railml_ocps.id'))
    ocp_type = db.Column(db.String(255))
    stop_description = db.Column(db.String(255))
    train_reverse = db.Column(db.Boolean)

    times = db.relationship("TimetableTime", lazy="dynamic")
    section = db.relationship("TimetableSection", lazy=True)
    ocp = db.relationship("RailMlOcp", lazy=True)

    @hybrid_property
    def scheduled_time(self):
        return self.times.filter(TimetableTime.scope == "scheduled").scalar()


class TimetableTime(db.Model):
    __tablename__ = 'timetable_times'

    def __repr__(self):
        return f"TimetableTime {self.id} {self.scope} – arrival: {self.arrival}, departure: {self.departure}"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timetable_ocp_id = db.Column(db.Integer, db.ForeignKey('timetable_ocps.id', ondelete='CASCADE', onupdate='CASCADE'))
    scope = db.Column(db.String(255))
    arrival = db.Column(db.Time)
    departure = db.Column(db.Time)
    arrival_day = db.Column(db.Integer)
    departure_day = db.Column(db.Integer)

    @property
    def arrival_with_day(self):
        arrival_with_day = self._time_with_day(time=self.arrival, day_addition=self.arrival_day)
        return arrival_with_day

    @property
    def departure_with_day(self):
        departure_with_day = self._time_with_day(time=self.departure, day_addition=self.departure_day)
        return departure_with_day

    def _time_with_day(self, time, day_addition):
        if time is not None:
            if day_addition is None:
                day_addition = 0

            day = START_DATE + datetime.timedelta(days=day_addition)
            time_with_day = datetime.datetime.combine(day, time)

        else:
            time_with_day = None
        return time_with_day


class TimetableSection(db.Model):
    __tablename__ = 'timetable_sections'

    def __repr__(self):
        return f"Section {self.section} {self.minimal_run_time}"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timetable_ocp_id = db.Column(db.Integer, db.ForeignKey('timetable_ocps.id', ondelete='CASCADE', onupdate='CASCADE'))
    section = db.Column(db.String(255))
    line = db.Column(db.String(255))
    track_id = db.Column(db.String(510))  # TODO: Could be a foreign key if necessary
    direction = db.Column(db.String(15))
    minimal_run_time = db.Column(db.Time)


class TimetableLine(db.Model):
    __tablename__ = "timetable_lines"

    def __repr__(self):
        return f"TimetableLine {self.id} {self.code}"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(255), unique=True, nullable=False)

    @property
    def all_trains(self):
        list_all_trains = []
        for tg in self.train_groups:
            for train in tg.trains:
                list_all_trains.append(train)
        return list_all_trains

    # TODO: Hier train cycle einfügen
    @hybrid_method
    def get_train_cycle(self, wait_time=datetime.timedelta(minutes=5)):
        list_all_trains = self.all_trains
        train_cycles_all = []

        while len(list_all_trains) > 0:

            first_train = self._get_earliest_departure(list_all_trains)
            list_all_trains.remove(first_train)
            train_cycle = [first_train]
            turning_information = []

            previous_train = first_train
            while True:
                next_train, time_information = self._get_next_train(previous_train=previous_train,
                                                              list_all_trains=list_all_trains, wait_time=wait_time)
                if next_train is None:
                    train_cycles_all.append(train_cycle)
                    break
                else:
                    list_all_trains.remove(next_train)
                    train_cycle.append(next_train)
                    turning_information.append([previous_train.train_part.last_ocp.ocp, previous_train,
                                                previous_train.train_part.last_ocp_arrival, time_information,
                                                next_train.train_part.first_ocp_departure, next_train])
                    previous_train = next_train

        return train_cycles_all

    def _get_next_train(self, previous_train, list_all_trains, wait_time=datetime.timedelta(minutes=5)):
        # TODO: Add minimum wait time
        next_train = None
        time_information = None

        # get the ocp where the trains end
        ocp = previous_train.train_part.last_ocp.ocp
        arrival = previous_train.train_part.last_ocp_arrival

        # search all trains that starts here
        possible_trains = dict()
        for train in list_all_trains:
            if train.train_part.first_ocp.ocp == ocp:
                train_departure = train.train_part.first_ocp_departure
                delta_time = train_departure - arrival
                if delta_time > datetime.timedelta(0):
                    possible_trains[delta_time] = train

        if possible_trains:
            next_train_time_delta = min(possible_trains)
            next_train = possible_trains[next_train_time_delta]
            time_information = next_train_time_delta

        return next_train, time_information


    def _get_earliest_departure(self, list_all_trains):
        """
        searches for the train with the earliest departure at their first stop
        :param list_all_trains:
        :return:
        """
        trains = dict()
        for train in list_all_trains:
            trains[train.train_part.first_ocp_departure] = train

        earliest_time = min(trains)
        earliest_train = trains[earliest_time]

        return earliest_train


class RailMlOcp(db.Model):
    __tablename__ = 'railml_ocps'

    def __repr__(self):
        return f"RailMlCop {self.id} {self.code} {self.name}"

    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255))
    code = db.Column(db.String(255))
    station_id = db.Column(db.Integer, db.ForeignKey('railway_stations.id'))
    operational_type = db.Column(db.String(31))

    station = db.relationship("RailwayStation", lazy=True)


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    budget_year = db.Column(db.Integer, nullable=False)
    lfd_nr = db.Column(db.String(100))
    fin_ve = db.Column(db.Integer, db.ForeignKey('finve.id'))
    bedarfsplan_number = db.Column(db.String(100))

    starting_year = db.Column(db.Integer)
    cost_estimate_original = db.Column(db.Integer)
    cost_estimate_last_year = db.Column(db.Integer)
    cost_estimate_actual = db.Column(db.Integer)
    cost_estimate_actual_third_parties = db.Column(db.Integer)
    cost_estimate_actual_equity = db.Column(db.Integer)  # Eigenanteil EIU
    cost_estimate_actual_891_01 = db.Column(db.Integer)
    cost_estimate_actual_891_02 = db.Column(db.Integer)
    cost_estimate_actual_891_03 = db.Column(db.Integer)
    cost_estimate_actual_891_04 = db.Column(db.Integer)
    cost_estimate_actual_891_91 = db.Column(db.Integer)

    delta_previous_year = db.Column(db.Integer)
    delta_previous_year_relativ = db.Column(db.Float)
    delta_previous_year_reasons = db.Column(db.Text)

    spent_two_years_previous = db.Column(db.Integer)
    spent_two_years_previous_third_parties = db.Column(db.Integer)
    spent_two_years_previous_equity = db.Column(db.Integer)
    spent_two_years_previous_891_01 = db.Column(db.Integer)
    spent_two_years_previous_891_02 = db.Column(db.Integer)
    spent_two_years_previous_891_03 = db.Column(db.Integer)
    spent_two_years_previous_891_04 = db.Column(db.Integer)
    spent_two_years_previous_891_91 = db.Column(db.Integer)

    allowed_previous_year = db.Column(db.Integer)
    allowed_previous_year_third_parties = db.Column(db.Integer)
    allowed_previous_year_equity = db.Column(db.Integer)
    allowed_previous_year_891_01 = db.Column(db.Integer)
    allowed_previous_year_891_02 = db.Column(db.Integer)
    allowed_previous_year_891_03 = db.Column(db.Integer)
    allowed_previous_year_891_04 = db.Column(db.Integer)
    allowed_previous_year_891_91 = db.Column(db.Integer)

    spending_residues = db.Column(db.Integer)
    spending_residues_891_01 = db.Column(db.Integer)
    spending_residues_891_02 = db.Column(db.Integer)
    spending_residues_891_03 = db.Column(db.Integer)
    spending_residues_891_04 = db.Column(db.Integer)
    spending_residues_891_91 = db.Column(db.Integer)

    year_planned = db.Column(db.Integer)
    year_planned_third_parties = db.Column(db.Integer)
    year_planned_equity = db.Column(db.Integer)
    year_planned_891_01 = db.Column(db.Integer)
    year_planned_891_02 = db.Column(db.Integer)
    year_planned_891_03 = db.Column(db.Integer)
    year_planned_891_04 = db.Column(db.Integer)
    year_planned_891_91 = db.Column(db.Integer)

    next_years = db.Column(db.Integer)
    next_years_third_parties = db.Column(db.Integer)
    next_years_equity = db.Column(db.Integer)
    next_years_891_01 = db.Column(db.Integer)
    next_years_891_02 = db.Column(db.Integer)
    next_years_891_03 = db.Column(db.Integer)
    next_years_891_04 = db.Column(db.Integer)
    next_years_891_91 = db.Column(db.Integer)

    finve = db.relationship("FinVe", backref=db.backref("budgets"))


class FinVe(db.Model):
    """
    FinVe = Finanzierungsvereinbarung
    a agreement between the state of germany and the infrastructure company to finance infrastructure. It's a little complicated
    """
    __tablename__ = 'finve'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    starting_year = db.Column(db.Integer)
    cost_estimate_original = db.Column(db.Integer)

    project_contents = db.relationship('ProjectContent', secondary=finve_to_projectcontent,
                                       backref=db.backref('finve', lazy=True))


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
