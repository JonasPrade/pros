import datetime
import jwt
import geojson
import geoalchemy2
import pandas
import shapely
import sqlalchemy
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
import json
import math
import logging
import os
import networkx
import time


from prosd import db, app, bcrypt, parameter
from prosd.postgisbasics import PostgisBasics
from prosd.calculation_methods.use import BvwpSgv, BvwpSpfv, BvwpSpnv, StandiSpnv
from prosd.calculation_methods.base import BaseCalculation


dirname = os.path.dirname(__file__)
filepath_recalculate = os.path.realpath(os.path.join(dirname, '../example_data/railgraph/recalculate_traingroups.json'))

START_DATE = datetime.datetime(parameter.START_YEAR, parameter.START_MONTH, parameter.START_DATE)
tractions = parameter.TRACTIONS


def get_calculation_method(traingroup, traction):
    match traingroup.category.transport_mode:
        case "sgv":
            calculation_method = 'bvwp'
        case "spfv":
            if traction in parameter.SPFV_STANDI_METHOD:
                calculation_method = 'standi'
            else:
                calculation_method = 'bvwp'
        case "spnv":
            calculation_method = 'standi'
        case other:
            calculation_method = None

    return calculation_method


def write_geojson_recalculate_traingroup(route, traingroups):
    try:
        with open(filepath_recalculate, 'r') as openfile:
            geojson_data = json.load(openfile)
    except json.decoder.JSONDecodeError:
        geojson_data = dict()
        geojson_data["traingroups"] = list()
        geojson_data["routes"] = list()

    # geojson_data = dict()
    geojson_data["recalculate_complete_graph"] = True
    for tg in traingroups:
        geojson_data["traingroups"].append(tg)

    if isinstance(geojson_data["routes"], int):
        geojson_data["routes"] = [geojson_data["routes"]]
        geojson_data["routes"].append(route)
    elif isinstance(geojson_data["routes"], list):
        geojson_data["routes"].append(route)
    elif geojson_data["routes"] is None:
        geojson_data["routes"] = [route]

    with open(filepath_recalculate, "w") as outfile:
        json.dump(geojson_data, outfile)


def get_lines_with_same_traingroups(line, scenario_id, area_lines):
    lines_id = [line.id for line in area_lines]

    traingroups_line = line.get_traingroup_for_scenario(scenario_id=scenario_id)
    traingroup_line_ids = [tg.id for tg in traingroups_line]
    # query all railway_lines that have exactly the same traingroups
    lines_same_traingroups = RailwayLine.query.join(RouteTraingroup).join(TimetableTrainGroup).filter(
        TimetableTrainGroup.id.in_(traingroup_line_ids),
        RailwayLine.id.in_(lines_id),
        RouteTraingroup.master_scenario_id == scenario_id
    ).group_by(RailwayLine).having(
        sqlalchemy.func.count(sqlalchemy.distinct(TimetableTrainGroup.id)) == len(traingroup_line_ids)
    ).all()

    # this query returns all lines that contain that traingroups. But there can be lines that have more than this traingroups. That has to be removed.
    traingroups = set(traingroups_line)
    lines_only_that_traingroups = []
    for rw_line in lines_same_traingroups:
        traingroups_of_rwline = set(rw_line.get_traingroup_for_scenario(scenario_id=scenario_id))
        if traingroups == traingroups_of_rwline:
            lines_only_that_traingroups.append(rw_line)

    if len(lines_only_that_traingroups)== 0:
        raise SubAreaError(
            f"{line} for {scenario_id} has no traingroups that uses that line"
        )
    return lines_only_that_traingroups


def get_next_train(previous_train, list_all_trains, wait_time=datetime.timedelta(minutes=5)):
    # get the ocp where the trains end
    ocp = previous_train.train_part.last_ocp.ocp
    arrival = previous_train.train_part.last_ocp_arrival

    # search all trains that starts here
    list_all_trains_filtered = list_all_trains[list_all_trains.first_ocp == ocp]
    list_all_trains_filtered = list_all_trains_filtered[list_all_trains_filtered.departure > arrival + wait_time]
    try:
        next_train = list_all_trains_filtered.iloc[0][0]
        # time_information = next_train.train_part.first_ocp_departure - arrival
    except IndexError:
        next_train = None

    return next_train


def get_earliest_departure(list_all_trains):
    """
    searches for the train with the earliest departure at their first stop
    :param list_all_trains:
    :return:
    """
    list_all_trains = list_all_trains.sort_values('departure')

    earliest_train = list_all_trains.iloc[0][0]

    return earliest_train


class PointOfLineNotAtEndError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoSplitPossibleError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoTractionFound(Exception):
    def __init__(self, message):
        super().__init__(message)


class SubAreaError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoTrainCostError(Exception):
    def __init__(self, message):
        super().__init__(message)


# be careful: no index of geo-coordinates of states and counties

# m:n tables

# project to group
projectcontent_to_group = db.Table('projectcontent_to_group',
                                   db.Column('projectcontent_id', db.Integer,
                                             db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                   db.Column('projectgroup_id', db.Integer,
                                             db.ForeignKey('project_groups.id', onupdate='CASCADE', ondelete='CASCADE')),
                                   db.Index('projectcontent_to_group_index', 'projectcontent_id', 'projectgroup_id')
                                   )

# project to railway Lines
projectcontent_to_line = db.Table('projectcontent_to_lines',
                                  db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                  db.Column('railway_lines_id', db.Integer, db.ForeignKey('railway_lines.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))
                                  )

projectcontent_to_railwaystations = db.Table('projectcontent_to_railwaystations',
                                             db.Column('projectcontent_id', db.Integer,
                                                       db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                             db.Column('railway_station_id', db.Integer,
                                                       db.ForeignKey('railway_stations.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))

                                             )

texts_to_project_content = db.Table('texts_to_projects',
                                    db.Column('project_content_id', db.Integer, db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                    db.Column('text_id', db.Integer, db.ForeignKey('texts.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))
                                    )

project_contents_to_states = db.Table('projectcontent_to_states',
                                      db.Column('project_content_id', db.Integer,
                                                db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                      db.Column('states_id', db.Integer, db.ForeignKey('states.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))
                                      )

project_contents_to_counties = db.Table('projectcontent_to_counties',
                                        db.Column('project_content_id', db.Integer,
                                                  db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                        db.Column('counties_id', db.Integer, db.ForeignKey('counties.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))
                                        )

project_contents_to_constituencies = db.Table('projectcontent_to_constituencies',
                                              db.Column('project_content_id', db.Integer,
                                                        db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                              db.Column('constituencies_id', db.Integer,
                                                        db.ForeignKey('constituencies.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))
                                              )

railway_nodes_to_railway_routes = db.Table('nodes_to_routes',
                                           db.Column('node_id', db.Integer,
                                                     db.ForeignKey('railway_nodes.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                           db.Column('route_id', db.Integer, db.ForeignKey('railway_route.id', onupdate='CASCADE',
                                                           ondelete='CASCADE'))
                                           )

formations_to_vehicles = db.Table('formations_to_vehicles', db.Model.metadata,
                                  db.Column('id', db.Integer, primary_key=True, autoincrement=True),
                                  db.Column('formation_id', db.String(100), db.ForeignKey('formations.id')),
                                  db.Column('vehicle_id', db.String(100), db.ForeignKey('vehicles.id'))
                                  )


finve_to_projectcontent = db.Table('finve_to_projectcontent',
                                   db.Column('finve_id', db.Integer, db.ForeignKey('finve.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                   db.Column('pc_id', db.Integer, db.ForeignKey('projects_contents.id', onupdate='CASCADE',
                                                           ondelete='CASCADE')),
                                   sqlalchemy.PrimaryKeyConstraint('finve_id', 'pc_id')
                                   )

tunnel_to_railwaylines = db.Table('rltunnel_to_rllines',
                                  db.Column('railway_tunnels_id', db.Integer, db.ForeignKey('railway_tunnels.id')),
                                  db.Column('railway_lines_id', db.Integer, db.ForeignKey('railway_lines.id'))
                                  )

bridges_to_railwaylines = db.Table('rwbridges_to_rwlines',
                                   db.Column('rw_bridges_id', db.Integer, db.ForeignKey('railway_bridges.id')),
                                   db.Column('rw_lines.id', db.Integer, db.ForeignKey('railway_lines.id'))
                                   )

traingroups_to_masterareas = db.Table('tg_to_masterareas',
                                       db.Column('traingroup_id', db.String(255), db.ForeignKey('timetable_train_groups.id')),
                                       db.Column('masterarea_id', db.Integer, db.ForeignKey('master_areas.id'))
                                       )

railwaylines_to_masterareas = db.Table('rwl_to_masterareas',
                                       db.Column('railwayline_id', db.Integer, db.ForeignKey('railway_lines.id')),
                                       db.Column('masterarea_id', db.Integer, db.ForeignKey('master_areas.id'))
                                       )

projectcontents_to_masterareas = db.Table('pc_to_masterareas',
                                          db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                          db.Column('masterarea_id', db.Integer, db.ForeignKey('master_areas.id'))
                                          )

projectcontents_to_masterscenario = db.Table('pc_to_masterscenario',
                                             db.Column('projectcontent_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                             db.Column('masterscenario_id', db.Integer, db.ForeignKey('master_scenarios.id'))
                                             )

# classes/Tables


class RailwayLine(db.Model):
    """
    defines a RailwayLine, which is part of a railway network and has geolocated attributes (Multiline oder Line).
    The RailwayLine are small pieces of rail, because they can quickly change attributes like allowed speed.
    A RailwayLine is part of a RailRoute (German: VzG)
    """

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
    voltage = db.Column(db.Float, default=None, comment="[kV]")
    dc_ac = db.Column(db.String(3), default=None)
    number_tracks = db.Column(db.String(100))  # eingleisig, zweigleisig
    vmax = db.Column(db.String(20))
    type_of_transport = db.Column(db.String(20))  # Pz-Bahn, Gz- Bahn, Pz/Gz-Bahn, S-Bahn, Hafenbahn, Seilzugbahn
    strecke_kuerzel = db.Column(db.String(100))
    bahnart = db.Column(db.String(100))
    active_until = db.Column(db.Integer)
    active_since = db.Column(db.Integer)
    closed = db.Column(db.Boolean, default=False)
    coordinates = db.Column(geoalchemy2.Geometry(geometry_type='LINESTRING', srid=4326), nullable=False)
    railway_infrastructure_company = db.Column(db.Integer,
                                               db.ForeignKey('railway_infrastructure_company.id', ondelete='SET NULL'))
    abs_nbs = db.Column(db.String(5), default='KS')
    gauge = db.Column(db.Integer, default=1435)

    # manipulate_geodata_and_db
    start_node = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', ondelete='SET NULL'))
    end_node = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', ondelete='SET NULL'))

    traingroups = db.relationship("RouteTraingroup", back_populates="railway_line")

    @hybrid_property
    def nodes(self):
        nodes = []
        nodes.append(self.start_node)
        nodes.append(self.end_node)
        return nodes

    @property
    def stations(self):
        """
        the models of nodes
        :return:
        """
        stations = []
        start_node = RailwayNodes.query.get(self.start_node)
        try:
            start_station = start_node.point[0].station
            stations.append(start_station)
        except IndexError:
            pass

        end_node = RailwayNodes.query.get(self.end_node)
        try:
            end_station = end_node.point[0].station
            stations.append(end_station)
        except IndexError:
            pass

        return stations

    @property
    def geojson(self):
        coords = geoalchemy2.shape.to_shape(self.coordinates)
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

        railline = line_old
        db.session.expunge(railline)
        db.make_transient(railline)
        railline.id = None
        railline.coordinates = coordinates_wkb

        railline_start_coordinate = \
            db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_StartPoint(coordinates_wkb))).one()[0]
        railline.start_node = RailwayNodes.add_node_if_not_exists(railline_start_coordinate).id
        railline_end_coordinates = \
            db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_EndPoint(coordinates_wkb))).one()[0]
        railline.end_node = RailwayNodes.add_node_if_not_exists(railline_end_coordinates).id

        pgis_basics = PostgisBasics(geometry=railline.coordinates, srid=4326)
        length = round(pgis_basics.length_in_meter())
        railline.length = length

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
                        1 / 80000000
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


        if len(coordinates) < 2 or len(coordinates) > 3:
            raise NoSplitPossibleError(
                "For line " + str(old_line.id) + " at point " + str(
                    shapely.wkb.loads(blade_point.desc, hex=True)) + " not possible"
            )
        elif len(coordinates) == 2:
            coordinates_newline_1 = coordinates[0][0]
            coordinates_newline_2 = coordinates[1][0]
        elif len(coordinates) == 3:
            coordinates_1 = db.session.execute(
                sqlalchemy.select(geoalchemy2.func.ST_Force2D(coordinates[0][0].split(",")[1][:-1]))).scalar()
            coordinates_2 = db.session.execute(
                sqlalchemy.select(geoalchemy2.func.ST_Force2D(coordinates[1][0].split(",")[1][:-1]))).scalar()

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

        project_contents = old_line.project_content
        masterareas = old_line.master_areas.copy()

        traingroups_list = db.session.query(TimetableTrainGroup.id).join(RouteTraingroup).filter(RouteTraingroup.railway_line_id==old_line.id).all()
        traingroups = []
        for row in traingroups_list:
            traingroups.append(row[0])
        route = old_line.route_number

        write_geojson_recalculate_traingroup(route=route, traingroups=traingroups)

        newline_1 = self.create_railline_from_old(line_old=old_line, coordinates=coordinates_newline_1)
        old_line = RailwayLine.query.filter(RailwayLine.id == old_line_id).one()
        newline_2 = self.create_railline_from_old(line_old=old_line, coordinates=coordinates_newline_2)

        old_line = RailwayLine.query.filter(RailwayLine.id == old_line_id).one()
        db.session.delete(old_line)
        db.session.commit()

        # add project_contents to the new lines
        objects = []
        for pc in project_contents:
            pc.railway_lines.append(newline_1)
            pc.railway_lines.append(newline_2)
            objects.append(pc)
        db.session.add_all(objects)
        db.session.commit()

        objects = []
        for area in masterareas:
            area.railway_lines.append(newline_1)
            area.railway_lines.append(newline_2)
            objects.append(area)
        db.session.add_all(objects)
        db.session.commit()

        # add routes and traingroups to a json so that can be recalculated

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
        line_nodes = line.nodes
        line_nodes.remove(node1_id)
        node2_id = line_nodes[0]
        node_2 = RailwayNodes.query.get(node2_id)

        return node_2

    @classmethod
    def get_next_point_of_line(self, line, point, allowed_distance=1 / 222000):
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
            logging.warning("Could not calculate angle(radian) for " + str(line1.id) + " and " + str(
                line2.id) + " angle rad is " + str(angle_rad))
        return angle_check

    def get_traingroup_for_scenario(self, scenario_id):
        traingroups = TimetableTrainGroup.query.join(RouteTraingroup).filter(
            sqlalchemy.and_(
                RouteTraingroup.master_scenario_id == scenario_id,
                RouteTraingroup.railway_line_id == self.id)
        ).all()
        return traingroups

    @property
    def get_neighbouring_lines(self):
        nodes = []
        for node in self.nodes:
            nodes.append(RailwayNodes.query.get(node))

        lines = set()
        for node in nodes:
            lines.update(node.lines)

        lines.discard(self)

        return lines


class RailwayPoint(db.Model):
    __tablename__ = 'railway_points'
    id = db.Column(db.Integer, primary_key=True)
    mifcode = db.Column(db.String(255))
    station_id = db.Column(db.Integer, db.ForeignKey('railway_stations.id', ondelete='SET NULL'))
    route_number = db.Column(db.Integer, db.ForeignKey('railway_route.number', onupdate='CASCADE', ondelete='SET NULL'))
    richtung = db.Column(db.Integer)
    km_i = db.Column(db.Integer)
    km_l = db.Column(db.String(255))
    name = db.Column(db.String(255))
    type = db.Column(db.String(255))  # db.Enum(allowed_values_type_of_station)
    db_kuerzel = db.Column(db.String(6))
    coordinates = db.Column(geoalchemy2.Geometry(geometry_type='POINTZ', srid=4326), nullable=False)
    node_id = db.Column(db.Integer, db.ForeignKey('railway_nodes.id', onupdate='CASCADE', ondelete='SET NULL'))
    height_ors = db.Column(db.Float)  # height calculated by openrouteservice.org

    # References
    # projects_start = db.relationship('Project', backref='project_starts', lazy=True)
    # projects_end = db.relationship('Project', backref='project_ends', lazy=True)

    @classmethod
    def get_line_of_route_that_intersects_point(self, coordinate, route_number, allowed_distance_in_node=1 / 2220000):
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
            allowed_distance_in_node = allowed_distance_in_node * 10
            line = RailwayLine.query.filter(
                geoalchemy2.func.ST_DWithin(RailwayLine.coordinates, coordinate, allowed_distance_in_node),
                RailwayLine.route_number == route_number
            ).one()

        return line

    @property
    def geojson(self):
        """
        returns a geojson for that point
        :return:
        """
        coordinate = geoalchemy2.shape.to_shape(self.coordinates)
        xy = coordinate.xy
        x = xy[0][0]
        y = xy[1][0]
        coordinate_geojson = geojson.Point((x, y))
        return coordinate_geojson


class RailwayStation(db.Model):
    """
    a railway point is always connected with one route. The station collects all railway_points of the same station
    """
    __tablename__ = 'railway_stations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    db_kuerzel = db.Column(db.String(6), unique=True)
    type = db.Column(db.String(10))
    charging_station = db.Column(db.Boolean, default=False)
    small_charging_station = db.Column(db.Boolean, default=False)

    railway_points = db.relationship("RailwayPoint", lazy="dynamic", backref="station")
    railway_nodes = db.relationship("RailwayNodes",
                                    secondary="join(RailwayPoint, RailwayNodes, RailwayPoint.node_id == RailwayNodes.id)",
                                    viewonly=True)

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
    __tablename__ = 'railway_nodes'
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
    def add_node_if_not_exists(self, coordinate, allowed_distance_in_node=1 / 222000):
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

        # if not isinstance(coordinate, str):
        #     coordinate = db.session.execute(
        #         db.session.query(
        #         geoalchemy2.func.ST_GeogFromWKB(coordinate)
        #         )).one()[0]

        return coordinate

    @classmethod
    def check_if_nodes_exists_for_coordinate(self, coordinate, allowed_distance_in_node=1 / 222000):
        """

        :param coordinate:
        :param allowed_distance_in_node:
        :return node: models.RailwayNode, if there is no node it returns a None
        """
        try:
            node = RailwayNodes.query.filter(geoalchemy2.func.ST_DWithin(RailwayNodes.coordinate, coordinate,
                                                                         allowed_distance_in_node)).scalar()
        except sqlalchemy.exc.MultipleResultsFound:
            allowed_distance_in_node = allowed_distance_in_node * (1 / 100)
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


class RailwayElectricityStation(db.Model):
    """

    """
    __tablename__ = 'railway_electricity_stations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    location = db.Column(db.String(255))
    code = db.Column(db.String(20))
    switching_station_id = db.Column(db.Integer, db.ForeignKey('railway_electricity_switching_stations.id'))
    electricity_station_type_id = db.Column(db.Integer, db.ForeignKey('railway_electricity_station_types.id'))
    equipment_15kv_year = db.Column(db.Integer)
    equipment_110kv_year = db.Column(db.Integer)
    equipment_station_year = db.Column(db.Integer)
    number = db.Column(db.Integer)
    station_id = db.Column(db.Integer, db.ForeignKey('railway_stations.id'))


class RailwayElectricitySwitchingStation(db.Model):
    __tablename__ = 'railway_electricity_switching_stations'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    location = db.Column(db.String(255))
    code = db.Column(db.String(20))
    station_id = db.Column(db.Integer, db.ForeignKey('railway_stations.id'))


class RailwayElectricityStationType(db.Model):
    """

    """
    __tablename__ = 'railway_electricity_station_types'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    decentral = db.Column(db.Boolean)


class RailwayTunnel(db.Model):
    """
    RailwayTunnels from db open data portal
    """
    __tablename__ = 'railway_tunnels'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_number_id = db.Column(db.Integer, db.ForeignKey('railway_route.number'))
    richtung = db.Column(db.Integer)
    von_km_i = db.Column(db.BigInteger)
    bis_km_i = db.Column(db.BigInteger)
    von_km_l = db.Column(db.String(100))
    bis_km_l = db.Column(db.String(100))
    length = db.Column(db.Float)
    name = db.Column(db.String(255))
    geometry = db.Column(geoalchemy2.Geometry(geometry_type='LINESTRINGZ', srid=4326), nullable=False)

    rw_lines = db.relationship('RailwayLine', secondary=tunnel_to_railwaylines,
                               backref=db.backref('rw_tunnels', lazy=True))


class RailwayBridge(db.Model):
    """

    """
    __tablename__ = 'railway_bridges'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_number_id = (db.Column, db.Integer, db.ForeignKey('railway_route.number'))
    direction = db.Column(db.Integer)
    von_km_i = db.Column(db.BigInteger)
    bis_km_i = db.Column(db.BigInteger)
    von_km_l = db.Column(db.String(100))
    bis_km_l = db.Column(db.String(100))
    length = db.Column(db.Float)
    geometry = db.Column(geoalchemy2.Geometry(geometry_type='LINESTRINGZ', srid=4326), nullable=False)

    rw_lines = db.relationship('RailwayLine', secondary=bridges_to_railwaylines,
                               backref=db.backref('rw_bridges', lazy=True))


class Project(db.Model):
    """
    defines a Project which can be related with (different) project contents and is connected m:n to RailwayLine
    """
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    superior_project_content_id = db.Column(db.Integer, db.ForeignKey(
        'projects_contents.id', onupdate='SET NULL', ondelete='SET NULL'))

    # references
    project_contents = db.relationship('ProjectContent', backref='project', lazy=True,
                                       foreign_keys="ProjectContent.project_id")
    superior_project = db.relationship("ProjectContent", backref='sub_project',
                                       foreign_keys=[superior_project_content_id])

    def __init__(self, name, description='', superior_project_id=None):
        self.name = name
        self.description = description
        self.superior_project = superior_project_id


class ProjectContent(db.Model):
    __tablename__ = 'projects_contents'

    # Basic informations
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', onupdate='SET NULL', ondelete='SET NULL', name='projects_contents_project_id_fkey'))
    project_number = db.Column(
        db.String(50))  # string because bvwp uses strings vor numbering projects, don't ask
    superior_project_content_id = db.Column(db.Integer, db.ForeignKey('projects_contents.id', onupdate='CASCADE', ondelete='CASCADE'))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default=None)
    reason_project = db.Column(db.Text, default=None)
    bvwp_alternatives = db.Column(db.Text, default=None)
    effects_passenger_long_rail = db.Column(db.Boolean, default=False)
    effects_passenger_local_rail = db.Column(db.Boolean, default=False)
    effects_cargo_rail = db.Column(db.Boolean, default=False)

    # economical data
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
    hoai = db.Column(db.Integer, nullable=False, default=0)  # 1 LP_1/2; 3 LP_3/4; 5 LP_5/9; 10 IBN erfolgt;
    parl_befassung_planned = db.Column(db.Boolean, nullable=False, default=False)
    parl_befassung_date = db.Column(db.Date)
    ro_finished = db.Column(db.Boolean, nullable=False, default=False)  # Raumordnung
    ro_finished_date = db.Column(db.Date)
    pf_finished = db.Column(db.Boolean, nullable=False, default=False)  # Planfeststellung fertiggestellt?
    pf_finished_date = db.Column(db.Date)
    bvwp_duration_of_outstanding_planning = db.Column(db.Float)
    bvwp_duration_of_build = db.Column(db.Float)
    bvwp_duration_operating = db.Column(db.Float)
    lp_12 = db.Column(db.Integer)  # 0= nicht begonnen, -1= keine Aktivität, 1 = läuft, 2 = fertig, -2=unbekannt
    lp_34 = db.Column(db.Integer)  # 0= nicht begonnen, 1 = läuft, 2 = fertig
    bau = db.Column(db.Integer)  # 0= nicht begonnen, 1 = läuft, 2 = fertig
    ibn_erfolgt = db.Column(db.Integer) # 0= nicht begonnen, 1 = läuft, 2 = fertig

    # properties of project
    nbs = db.Column(db.Boolean, nullable=False, default=False)
    abs = db.Column(db.Boolean, nullable=False, default=False)
    elektrification = db.Column(db.Boolean, nullable=False, default=False)
    charging_station = db.Column(db.Boolean, default=False)
    small_charging_station = db.Column(db.Boolean, default=False)
    second_track = db.Column(db.Boolean, nullable=False, default=False)
    third_track = db.Column(db.Boolean, nullable=False, default=False)
    fourth_track = db.Column(db.Boolean, nullable=False, default=False)
    curve = db.Column(db.Boolean, nullable=False, default=False)  # Neue Verbindungskurve
    platform = db.Column(db.Boolean, nullable=False, default=False)  # Neuer Bahnsteig
    junction_station = db.Column(db.Boolean, nullable=False, default=False)
    number_junction_station = db.Column(db.Integer)
    overtaking_station = db.Column(db.Boolean, nullable=False, default=False)
    number_overtaking_station = db.Column(db.Integer)
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
    battery = db.Column(db.Boolean, default=False)
    h2 = db.Column(db.Boolean, default=False)
    efuel = db.Column(db.Boolean, default=False)
    closure = db.Column(db.Boolean, default=False)  # close of rail
    optimised_electrification = db.Column(db.Boolean, default=False)
    filling_stations_efuel = db.Column(db.Boolean, default=False)
    filling_stations_h2 = db.Column(db.Boolean, default=False)
    filling_stations_diesel = db.Column(db.Boolean, default=False)
    filling_stations_count = db.Column(db.Integer, default=0)
    sanierung = db.Column(db.Boolean, default=False)
    sgv740m = db.Column(db.Boolean, default=False)
    railroad_crossing = db.Column(db.Boolean, default=False)  # Änderungen an Bahnübergängen
    new_estw = db.Column(db.Boolean, default=False)
    new_dstw = db.Column(db.Boolean, default=False)
    noise_barrier = db.Column(db.Boolean, default=False)  # alle Lärmschutzmaßnahmen
    overpass = db.Column(db.Boolean, default=False)  # Überleitstellen
    buffer_track = db.Column(db.Boolean, default=False)  # Puffergleis
    gwb = db.Column(db.Boolean, default=False)  # Gleiswechselbetrieb
    simultaneous_train_entries = db.Column(db.Boolean, default=False)  # gleichzeitige Zugeinfahrten
    tilting = db.Column(db.Boolean, default=False)

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
    natura2000_not_excluded = db.Column(db.Float)
    natura2000_probably = db.Column(db.Float)
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
    maintenance_cost = db.Column(db.Float)
    investment_cost = db.Column(db.Float)
    planning_cost = db.Column(db.Float)
    capital_service_cost = db.Column(db.Float)
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

    # some additionale fields for Geojson and centroid to avoid anoying calculations
    geojson_representation = db.Column(db.Text)  # storing the GeoJSON as a text field
    centroid = db.Column(geoalchemy2.Geometry('POINT'))  # storing the centroid as a point geometry

    # relationships
    # project = db.relationship("Project", backref='project_contents', lazy=True, foreign_keys=[project_id])
    texts = db.relationship('Text', secondary=texts_to_project_content,
                            backref=db.backref('project_content', lazy=True))
    projectcontent_groups = db.relationship('ProjectGroup', secondary=projectcontent_to_group,
                                            backref=db.backref('projects_content', lazy=True))
    railway_lines = db.relationship('RailwayLine', secondary=projectcontent_to_line,
                                                   backref=db.backref('project_content', lazy=True))
    superior_project_content = db.relationship('ProjectContent', remote_side=[id], backref=db.backref('sub_project_contents'))
    railway_stations = db.relationship('RailwayStation', secondary=projectcontent_to_railwaystations,
                                       backref=db.backref('project_content', lazy=True))
    states = db.relationship("States", secondary=project_contents_to_states,
                             backref=db.backref('states', lazy=True))
    counties = db.relationship("Counties", secondary=project_contents_to_counties,
                               backref=db.backref('counties', lazy=True))
    constituencies = db.relationship("Constituencies", secondary=project_contents_to_constituencies,
                                     backref=db.backref('constituencies', lazy=True))

    # indexes
    superior_project_content_id_index = sqlalchemy.Index('superior_project_content_id_index', superior_project_content_id)

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
            pc.railway_lines.append(line)

        pc.generate_geojson()
        pc.compute_centroid()

        db.session.add(pc)
        db.session.commit()

    def generate_geojson(self):
        features = []

        # Add lines
        for line in self.railway_lines:
            coord = geoalchemy2.shape.to_shape(line.coordinates).simplify(0.01)  # Adjusted
            geometry = shapely.geometry.mapping(coord)
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": line.id,
                    "projectcontent_id": self.id
                }
            })

        # Add railway stations
        for station in self.railway_stations:
            station_centroid = geoalchemy2.shape.to_shape(station.coordinate_centroid)  # Adjusted for GeoAlchemy
            geometry = shapely.geometry.mapping(station_centroid)
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": station.id,
                    "name": station.name,
                    "projectcontent_id": self.id
                }
            })

        # Create FeatureCollection
        geojson_obj = {
            "type": "FeatureCollection",
            "features": features
        }

        self.geojson_representation = json.dumps(geojson_obj)

    def compute_centroid(self):
        # Convert RailwayLines to Shapely LineStrings
        line_geometries = [geoalchemy2.shape.to_shape(line.coordinates) for line in self.railway_lines]

        # Convert RailwayStations to Shapely Points
        point_geometries = [geoalchemy2.shape.to_shape(station.coordinate_centroid) for station in
                            self.railway_stations]

        # If you have both LineStrings and Points
        if line_geometries and point_geometries:
            combined = shapely.geometry.GeometryCollection(line_geometries + point_geometries)
        # If you only have LineStrings
        elif line_geometries:
            combined = shapely.geometry.MultiLineString(line_geometries)
        # If you only have Points
        else:
            combined = shapely.geometry.MultiPoint(point_geometries)

        centroid = combined.centroid
        self.centroid = geoalchemy2.WKTElement(centroid.wkt,
                                               srid=4326)  # Assuming a default SRID of 4326. Adjust if different.

    # This method can be called during creation or updating of a ProjectContent
    def update_geo_properties(self):
        self.generate_geojson()
        self.compute_centroid()

    def calc_progress_sub_projects(self):
        progress_sub_projects = {
            "pending": 0,
            "lp_12": 0,
            "lp_34": 0,
            "bau": 0,
            "ibn_erfolgt": 0,
            "not_known": 0,
            "has_sub_project": 0
        }

        if len(self.sub_project_contents) == 0:
            return progress_sub_projects

        for sub_project in self.sub_project_contents:
            if sub_project.lp_12 == 0:
                progress_sub_projects["pending"] += 1
            elif sub_project.lp_12 == 1:
                progress_sub_projects["lp_12"] += 1
            elif sub_project.lp_34 == 1:
                progress_sub_projects["lp_34"] += 1
            elif sub_project.bau == 1:
                progress_sub_projects["bau"] += 1
            elif sub_project.ibn_erfolgt == 2:
                progress_sub_projects["ibn_erfolgt"] += 1
            else:
                if sub_project.sub_project_contents:
                    progress_sub_projects["has_sub_project"] += 1
                else:
                    progress_sub_projects["not_known"] += 1

        return progress_sub_projects


class ProjectGroup(db.Model):
    __tablename__ = 'project_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    short_name = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    public = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(10), default="#FF0000")
    plot_only_superior_projects = db.Column(db.Boolean, default=True, comment='if true, only projects that have no superior project is plotted in frontend')

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
            if pc.project is not None:
                if pc.project.superior_project_content_id is None:
                    projects_id.add(pc.project)

        return projects_id

    @property
    def superior_project_contents(self):
        projects = set()
        for pc in self.projects_content:
            if pc.superior_project_content_id is None:
                projects.add(pc)
        return projects


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

    vehicle_pattern_spnv_id = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))
    vehicle_pattern_spfv_id = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))
    vehicle_pattern_sgv_id = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))

    vehicle_pattern_id = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))

    vehicle_pattern = db.relationship("VehiclePattern", foreign_keys=[vehicle_pattern_id], backref="vehicles")
    vehicle_pattern_spnv = db.relationship("VehiclePattern", foreign_keys=[vehicle_pattern_spnv_id])
    vehicle_pattern_spfv = db.relationship("VehiclePattern", foreign_keys=[vehicle_pattern_spfv_id])
    vehicle_pattern_sgv = db.relationship("VehiclePattern", foreign_keys=[vehicle_pattern_sgv_id])

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
    battery_capacity = db.Column(db.Float, default=None)

    vehicle_pattern_id_electrical = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))
    vehicle_pattern_id_h2 = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))
    vehicle_pattern_id_battery = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))
    vehicle_pattern_id_efuel = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))
    vehicle_pattern_id_diesel = db.Column(db.Integer, db.ForeignKey('vehicles_pattern.id'))

    vehicle_pattern_electrical = db.relationship('VehiclePattern', foreign_keys="VehiclePattern.vehicle_pattern_id_electrical", remote_side=[id])
    vehicle_pattern_h2 = db.relationship('VehiclePattern', foreign_keys="VehiclePattern.vehicle_pattern_id_h2", remote_side=[id])
    vehicle_pattern_battery = db.relationship('VehiclePattern', foreign_keys="VehiclePattern.vehicle_pattern_id_battery", remote_side=[id])
    vehicle_pattern_efuel = db.relationship('VehiclePattern', foreign_keys="VehiclePattern.vehicle_pattern_id_efuel", remote_side=[id])
    vehicle_pattern_diesel = db.relationship('VehiclePattern', foreign_keys="VehiclePattern.vehicle_pattern_id_diesel", remote_side=[id])


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
    formation_id_calculation_bvwp = db.Column(db.String(100), db.ForeignKey('formations.id'))
    formation_id_calculation_standi = db.Column(db.String(100), db.ForeignKey('formations.id'))

    vehicles = db.relationship("Vehicle", secondary=formations_to_vehicles, backref="formations")
    formation_calculation_bvwp = db.relationship("Formation", foreign_keys="Formation.formation_id_calculation_bvwp", remote_side=[id])
    formation_calculation_standi = db.relationship("Formation", foreign_keys="Formation.formation_id_calculation_standi", remote_side=[id])

    @property
    def vehicles_composition(self):
        # vehicles can be associated multiple times to one formation. the relationship does not recognise that

        entry = db.session.query(Vehicle, formations_to_vehicles.c.id).join(formations_to_vehicles).join(Formation).filter(Formation.id == self.id).all()
        vehicles = []
        for row in entry:
            vehicles.append(row[0])

        return vehicles

    @property
    def vehicles_ids_composition(self):
        entry = db.session.query(Vehicle, formations_to_vehicles.c.id).join(formations_to_vehicles).join(
            Formation).filter(Formation.id == self.id).all()
        vehicles = {}
        for row in entry:
            vehicle = row[0]
            if vehicle.id in vehicles.keys():
                vehicles[vehicle.id] += 1
            else:
                vehicles[vehicle.id] = 1

        return vehicles

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
        additional_maintenance_cost_without_overhead = self.vehicles[
            0].vehicle_pattern.additional_maintenance_cost_withou_overhead
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


class TimetableTrainCost(db.Model):
    __tablename__ = 'timetable_train_cost'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    traingroup_id = db.Column(db.String(255), db.ForeignKey('timetable_train_groups.id'))
    calculation_method = db.Column(db.String(10))  # bvwp or standi
    master_scenario_id = db.Column(db.Integer, db.ForeignKey('master_scenarios.id'))
    traction = db.Column(db.String(255))  # electrification, efuel, h2, battery, diesel

    cost = db.Column(db.Integer, comment="sum of cost in T EUR per year")
    debt_service = db.Column(db.Integer)
    maintenance_cost = db.Column(db.Integer)
    energy_cost = db.Column(db.Integer)
    co2_cost = db.Column(db.Integer)
    pollutants_cost = db.Column(db.Integer)
    primary_energy_cost = db.Column(db.Integer)
    co2_emission = db.Column(db.Integer)
    energy = db.Column(db.Float)
    thg_vehicle_production_cost = db.Column(db.Integer)

    traingroup = db.relationship('TimetableTrainGroup', backref='train_costs')

    sqlalchemy.UniqueConstraint(traingroup_id, calculation_method, master_scenario_id, traction, name='unique_calculation')

    @classmethod
    def create(cls, traingroup, master_scenario_id, traction, infra_version, calculation_method=None):
        obj_attributes = dict()
        obj_attributes["traingroup_id"] = traingroup.id
        obj_attributes["master_scenario_id"] = master_scenario_id
        obj_attributes["traction"] = traction
        start_year_operation = parameter.START_YEAR
        duration_operation = parameter.DURATION_OPERATION

        if calculation_method is None:
            calculation_method = get_calculation_method(traingroup, traction)
        obj_attributes["calculation_method"] = calculation_method

        if calculation_method == 'bvwp':
            match traingroup.category.transport_mode:
                case "sgv":
                    if traction == 'h2' or traction == 'battery':
                        return None
                    utility = BvwpSgv(tg=traingroup, traction=traction, start_year_operation=start_year_operation, duration_operation=duration_operation, infra_version=infra_version)
                case "spfv":
                    utility = BvwpSpfv(tg=traingroup, traction=traction, start_year_operation=start_year_operation, duration_operation=duration_operation, infra_version=infra_version)
                case "spnv":
                    utility = BvwpSpnv(tg=traingroup, traction=traction, start_year_operation=start_year_operation, duration_operation=duration_operation, infra_version=infra_version)

            obj_attributes["cost"] = utility.use
            obj_attributes["debt_service"] = utility.debt_service_sum
            obj_attributes["maintenance_cost"] = utility.maintenance_cost_sum
            obj_attributes["energy_cost"] = utility.energy_cost_sum
            obj_attributes["co2_cost"] = utility.co2_energy_cost_sum
            obj_attributes["pollutants_cost"] = utility.pollutants_cost_sum
            obj_attributes["primary_energy_cost"] = utility.primary_energy_cost_sum
            obj_attributes["co2_emission"] = utility.co2_sum
            obj_attributes["thg_vehicle_production_cost"] = utility.emission_vehicle_production_cost

        elif calculation_method == 'standi':
            trainline = traingroup.traingroup_lines
            match traingroup.category.transport_mode:
                case "sgv":
                    logging.error("For SGV calculation method standi is not possible")
                    return None
                case "spfv":
                    utility = StandiSpnv(trainline=trainline, traction=traction, start_year_operation=start_year_operation, duration_operation=duration_operation, infra_version=infra_version)
                case "spnv":
                    utility = StandiSpnv(trainline=trainline, traction=traction,
                                 start_year_operation=start_year_operation, duration_operation=duration_operation, infra_version=infra_version)

            obj_attributes["cost"] = utility.use/len(trainline.train_groups)
            obj_attributes["debt_service"] = utility.debt_service_sum/len(trainline.train_groups)
            obj_attributes["maintenance_cost"] = utility.maintenance_cost_sum/len(trainline.train_groups)
            obj_attributes["energy_cost"] = utility.energy_cost_sum/len(trainline.train_groups)
            obj_attributes["co2_cost"] = utility.co2_energy_cost_sum/len(trainline.train_groups)
            obj_attributes["pollutants_cost"] = utility.pollutants_cost_sum/len(trainline.train_groups)
            obj_attributes["primary_energy_cost"] = utility.primary_energy_cost_sum/len(trainline.train_groups)
            obj_attributes["co2_emission"] = utility.co2_sum/len(trainline.train_groups)
            obj_attributes["thg_vehicle_production_cost"] = utility.emission_vehicle_production_cost/len(trainline.train_groups)

        obj = cls(
            **obj_attributes
        )
        try:
            db.session.add(obj)
            db.session.commit()
            return obj
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            logging.warning(f"Cost for {traingroup} for traction {traction} for scenario {master_scenario_id} with calculation_method {calculation_method}")
            return None


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
        return f"TrainGroup {self.id} {self.description}"

    id = db.Column(db.String(255), primary_key=True)
    code = db.Column(db.String(255))
    train_number = db.Column(db.Integer)
    traingroup_line = db.Column(db.String(255),
                                db.ForeignKey('timetable_lines.code', ondelete='SET NULL', onupdate='CASCADE'))

    trains = db.relationship("TimetableTrain", lazy=True, backref="train_group")
    traingroup_lines = db.relationship("TimetableLine", lazy=True, backref="train_groups")
    # lines = db.relationship("RailwayLine", secondary=traingroup_to_railwaylines, backref="train_groups")

    railway_lines = db.relationship("RouteTraingroup", back_populates='traingroup')

    @classmethod
    def get_cost_by_traction(self, obj, traction):
        match traction:
            case "electrification":
                cost = obj.cost_electro_renew
            case "efuel":
                cost = obj.cost_efuel
            case "battery":
                cost = obj.cost_battery
            case "h2":
                cost = obj.cost_h2
            case "diesel":
                cost = obj.diesel

        return cost

    @hybrid_method
    def railway_lines_scenario(self, scenario_id):
        rw_lines = RailwayLine.query.join(RouteTraingroup).filter(
            RouteTraingroup.master_scenario_id == scenario_id,
            RouteTraingroup.traingroup_id == self.id
        ).all()

        return rw_lines

    def railway_lines_scenario_infra_version(self, infra_version):
        rw_lines_id = db.session.query(RailwayLine.id).join(RouteTraingroup).filter(
            RouteTraingroup.master_scenario_id == infra_version.scenario.id,
            RouteTraingroup.traingroup_id == self.id
        ).all()

        rw_lines = list()

        for id in rw_lines_id:
            rw_lines.append(infra_version.get_railwayline_model(id))

        return rw_lines

    @hybrid_method
    def length_line(self, scenario_id):
        length_m = db.session.query(sqlalchemy.func.sum(RailwayLine.length)).join(RouteTraingroup).filter(
            RouteTraingroup.master_scenario_id == scenario_id,
            RouteTraingroup.traingroup_id == self.id
        ).one()
        length_km = length_m[0] / 1000
        return length_km

    @hybrid_method
    def length_line_no_catenary(self, infra_version):
        km = 0
        for line in self.railway_lines_scenario_infra_version(infra_version):
            if line.catenary is False:
                km += line.length / 1000

        return km

    @hybrid_method
    def running_km_day(self, scenario_id):
        running_km_day = self.length_line(scenario_id) * len(self.trains)

        return running_km_day  # in km

    @hybrid_method
    def running_km_day_abs(self, infra_version):
        running_km_day_abs = 0
        for line in self.railway_lines_scenario_infra_version(infra_version):
            if line.abs_nbs == "ABS":
                running_km_day_abs += line.length / 1000

        running_km_day_abs = running_km_day_abs * len(self.trains)
        return running_km_day_abs

    @hybrid_method
    def running_km_day_nbs(self, infra_version):
        running_km_day_nbs = 0
        for line in self.railway_lines_scenario_infra_version(infra_version):
            if line.abs_nbs == "NBS":
                running_km_day_nbs += line.length / 1000

        running_km_day_nbs = running_km_day_nbs * len(self.trains)
        return running_km_day_nbs

    @hybrid_method
    def running_km_day_no_catenary(self, infra_version):
        running_km_day_no_catenary = 0
        for line in self.railway_lines_scenario_infra_version(infra_version):
            if line.catenary is False:
                running_km_day_no_catenary += line.length / 1000

        running_km_day_no_catenary = running_km_day_no_catenary * len(self.trains)
        return running_km_day_no_catenary

    @hybrid_method
    def running_km_year(self, scenario_id):
        running_km_year = self.running_km_day(scenario_id) * 365 / 1000
        return running_km_year  # in Tsd. km

    @hybrid_method
    def running_km_year_abs(self, infra_version):
        running_km_year_abs = self.running_km_day_abs(infra_version) * 365 / 1000
        return running_km_year_abs

    @hybrid_method
    def running_km_year_nbs(self, infra_version):
        running_km_year_nbs = self.running_km_day_nbs(infra_version) * 365 / 1000
        return running_km_year_nbs

    @hybrid_method
    def running_km_year_no_catenary(self, infra_version):
        running_km_year_no_catenary = self.running_km_day_no_catenary(infra_version) * 365 / 1000
        return running_km_year_no_catenary

    @hybrid_property
    def minimal_run_time(self):
        train = self.trains[0]
        ocps = train.train_part.timetable_ocps
        minimal_run_time = datetime.timedelta(seconds=0)

        for ocp in ocps:
            sections = ocp.section
            for section in sections:
                section_time = section.minimal_run_time
                if section_time:
                    timedelta = datetime.timedelta(hours=section_time.hour, minutes=section_time.minute,
                                                   seconds=section_time.second)
                    minimal_run_time += timedelta
        return minimal_run_time

    @hybrid_property
    def travel_time(self):
        """
        includes stop_times (departure first to arrivel last)
        :return:
        """
        train = self.trains[0]
        departure_first_time = train.train_part.first_ocp.times.filter(
            TimetableTime.scope == "scheduled").one().departure
        arrival_last_time = train.train_part.last_ocp.times.filter(TimetableTime.scope == "scheduled").one().arrival
        departure_first = datetime.datetime.combine(datetime.date.today(), departure_first_time)
        arrival_last = datetime.datetime.combine(datetime.date.today(), arrival_last_time)
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
        running_time_year = (running_time_year.days * 24 + running_time_year.seconds / 3600) / 1000
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
                        stop_duration = datetime.datetime.combine(datetime.date.min,
                                                                  time.departure) - datetime.datetime.combine(
                            datetime.date.min, time.arrival)
                        stops_duration += stop_duration

        return stops_duration

    @hybrid_property
    def stops_duration_average(self):
        """
        average of the duration of a stop (first and last stop is ignored)
        :return:
        """
        stops_duration_average = (self.stops_duration / (self.stops_count - 2))
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

    @hybrid_method
    def travel_speed_average(self, infra_version):
        """
        The speed of the line including all stops
        :return:
        """
        travel_speed = self.length_line(infra_version.scenario.id)/(self.travel_time.seconds/3600)
        return travel_speed

    def calc_cost_road_transport(self):
        from prosd.graph.road import RoadDistances
        road_cost_per_100_km = sum(
            [parameter.ROAD_ENERGY_ELECTRO_RENWEABLE_COST,
            parameter.ROAD_PERSONAL_COST,
            parameter.ROAD_CAPITAL_COST,
            parameter.ROAD_MAINTENANCE_COST,
            parameter.ROAD_CO2_ELECTRO_RENEWABLE_COST,
            parameter.ROAD_PRIMARY_ENERGIE_ELECTRO_RENEWABLE_COST,
            parameter.ROAD_EMISSION_ELECTRO_RENEWABLE_COST]
        )/1000 # Tsd. Euro pro 100 km

        count_trucks = len(self.trains)*math.ceil(self.payload_train/parameter.PAYLOAD_TRUCK)
        rd = RoadDistances()
        road_km = rd.get_distance(
            from_ocp=self.first_ocp.ocp.code,
            to_ocp=self.last_ocp.ocp.code
        )/100  # in 100 km

        road_cost = count_trucks * road_km * road_cost_per_100_km
        return road_cost  # Tsd. € per day

    @property
    def get_wagon_sgv(self):
        """
        gets the wagon vehicle
        only works for sgv
        :return:
        """
        formation = self.trains[0].train_part.formation
        for vehicle in formation.vehicles:
            if vehicle.wagon is True:
                return vehicle

        return None

    @property
    def count_wagons(self):
        """
        calculate the count of wagons of the train
        condition: container train
        only works for sgv
        :return:
        """
        vehicle = self.get_wagon_sgv
        count_wagons_weight = math.ceil(vehicle.brutto_weight/(parameter.DEAD_WEIGHT_CONTAINER_WAGON + parameter.PAYLOAD_CONTAINER_WAGON))
        count_wagons_length = math.floor(vehicle.length/parameter.LENGTH_CONTAINER_WAGON)
        count_wagons = min(count_wagons_length, count_wagons_weight)
        return count_wagons

    @property
    def payload_train(self):
        """
        calculate the payload of sgv train
        :return:
        """
        payload_train = self.count_wagons * parameter.PAYLOAD_CONTAINER_WAGON

        return payload_train

    def wagon_cost_per_day(self, scenario_id):
        """
        the cost of the usage for wagons (including maintenance) for the traingroup for one day in thousand Euros
        :param scenario_id:
        :return:
        """
        usage_day = self.running_km_day(scenario_id)/parameter.AVERAGE_SPEED_RESILIENCE  # running_hours not used because timetable may not right at resilience case
        cost_wagons = parameter.COST_CONTAINER_WAGON * self.count_wagons * usage_day / 1000
        return cost_wagons

    def personnel_cost_per_day(self, scenario_id):
        """
        personell cost for a day in thousend euro
        :param scenario_id:
        :return:
        """
        personnel_hours_day = self.running_km_day(scenario_id)/parameter.AVERAGE_SPEED_RESILIENCE
        personnel_cost = personnel_hours_day * parameter.COST_TRAIN_DRIVER / 1000
        return personnel_cost

    @property
    def train_provision_cost_day(self):
        """
        train provision cost for a day in thousend euro

        :return:
        """
        count_wagons = self.count_wagons
        wagons_traingroup = count_wagons * len(self.trains)
        train_provision_cost = wagons_traingroup * parameter.TRAIN_PROVISION_COST_PER_WAGGON / 1000

        return train_provision_cost


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
        return f"TTTrainPart {self.id} {self.first_ocp.ocp.code} {self.first_ocp_departure} {self.last_ocp.ocp.code} {self.last_ocp_arrival}"

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
        # sqlalchemy.select([TimetableTrainPart.timetable_ocps]).where(TimetableOcp.train_part == cls.id).order_by(TimetableOcp.sequence).limit(1)
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


class TrainCycle(db.Model):
    __tablename__ = 'traincycles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trainline_id = db.Column(db.Integer, db.ForeignKey('timetable_lines.id'))
    wait_time = db.Column(db.Time)
    first_train_id = db.Column(db.String(510), db.ForeignKey('timetable_train.id'))

    elements = db.relationship("TrainCycleElement", backref="train_cycle")

    sqlalchemy.UniqueConstraint(
        trainline_id,
        wait_time,
        first_train_id,
        name='unique_traincycle'
    )

    @classmethod
    def get_train_cycles(obj, timetableline_id, wait_time=datetime.timedelta(minutes=5)):
        cycles = TrainCycle.query.filter(
            TrainCycle.trainline_id == timetableline_id,
            TrainCycle.wait_time == wait_time
        ).all()

        if len(cycles) == 0:
            logging.info(f"No traincycles found for timetableline {timetableline_id} and wait_time {wait_time}. Start calculating train_cycles")
            cycles = TrainCycle.calculate_train_cycles(
                timetableline_id=timetableline_id,
                wait_time=wait_time
            )

        return cycles

    @classmethod
    def calculate_train_cycles(cls, timetableline_id, wait_time=datetime.timedelta(minutes=5)):
        TrainCycle.delete_train_cycles(
            timetable_line_id=timetableline_id,
            wait_time=wait_time
        )

        trainline = TimetableLine.query.get(timetableline_id)
        list_all_trains = trainline.all_trains
        train_cycles_all = []

        while len(list_all_trains) > 0:
            first_train = get_earliest_departure(list_all_trains)
            list_all_trains = list_all_trains[list_all_trains.traingroup != first_train]
            train_cycle = TrainCycle(
                trainline_id=trainline.id,
                wait_time=wait_time,
                first_train_id=first_train.id
            )
            train_cycle_element = TrainCycleElement(
                train_cycle=train_cycle,
                train=first_train,
                sequence=0
            )
            train_cycle_elements = [train_cycle_element]

            previous_train = first_train
            while True:
                next_train = get_next_train(previous_train=previous_train,
                                                 list_all_trains=list_all_trains,
                                                 wait_time=wait_time)
                if next_train is None:
                    train_cycles_all.append(train_cycle)
                    break
                else:
                    list_all_trains = list_all_trains[list_all_trains.traingroup != next_train]
                    sequence = train_cycle_element.sequence + 1
                    train_cycle_element = TrainCycleElement(
                        train_cycle=train_cycle,
                        train=next_train,
                        sequence=sequence
                    )
                    train_cycle_elements.append(train_cycle_element)
                    previous_train = next_train


        db.session.add_all(train_cycles_all)
        db.session.commit()

        return train_cycles_all

    @classmethod
    def delete_train_cycles(cls, timetable_line_id, wait_time=datetime.timedelta(minutes=5)):
        TrainCycle.query.filter(
            TrainCycle.trainline_id == timetable_line_id,
            TrainCycle.wait_time == wait_time
        ).delete()


class TrainCycleElement(db.Model):
    __tablename__ = 'train_cycle_elements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    train_cycle_id = db.Column(db.Integer, db.ForeignKey('traincycles.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    train_id = db.Column(db.String(510), db.ForeignKey('timetable_train.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)

    train = db.relationship("TimetableTrain")


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
    track_id = db.Column(db.String(510))
    direction = db.Column(db.String(15))
    minimal_run_time = db.Column(db.Time)


class RouteTraingroup(db.Model):
    __tablename__ = 'route_traingroups'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    traingroup_id = db.Column(db.String(255), db.ForeignKey("timetable_train_groups.id"))
    railway_line_id = db.Column(db.Integer, db.ForeignKey("railway_lines.id"))
    section = db.Column(db.Integer)
    master_scenario_id = db.Column(db.Integer, db.ForeignKey('master_scenarios.id', ondelete='CASCADE', onupdate='CASCADE'))

    traingroup = db.relationship(TimetableTrainGroup, back_populates='railway_lines')
    railway_line = db.relationship(RailwayLine, back_populates='traingroups')
    master_scenario = db.relationship("MasterScenario", backref=db.backref("routes"))


class TimetableLine(db.Model):
    __tablename__ = "timetable_lines"

    def __repr__(self):
        return f"TimetableLine {self.id} {self.code}"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(255), unique=True, nullable=False)
    count_formations = db.Column(db.Integer, default=0)

    @property
    def travel_time(self):
        travel_time = datetime.timedelta(seconds=0)
        for tg in self.train_groups:
            travel_time += tg.travel_time

        return travel_time

    @property
    def running_time(self):
        running_time =datetime.timedelta(seconds=0)
        for tg in self.train_groups:
            running_time += tg.minimal_run_time

        return running_time

    @hybrid_method
    def length_line(self, infra_version):
        length = 0
        for tg in self.train_groups:
            length += tg.length_line(infra_version)
        return length

    @hybrid_method
    def running_km_year(self, scenario_id):
        running_km_year = 0
        for tg in self.train_groups:
            running_km_year += tg.running_km_year(scenario_id)

        return running_km_year

    @hybrid_method
    def running_km_year_no_catenary(self, infra_version):
        running_km_year_no_catenary = 0
        for tg in self.train_groups:
            running_km_year_no_catenary += tg.running_km_year_no_catenary(infra_version)

        return running_km_year_no_catenary

    @property
    def all_trains(self):
        columns = ['traingroup', 'departure', 'first_ocp']
        list_all_trains = list()
        for tg in self.train_groups:
            for train in tg.trains:
                list_all_trains.append([train, train.train_part.first_ocp_departure, train.train_part.first_ocp.ocp])
        df_all_trains = pandas.DataFrame(list_all_trains, columns=columns)
        df_all_trains = df_all_trains.sort_values('departure')
        return df_all_trains

    @property
    def start_ocps(self):
        trains = []
        for tg in self.train_groups:
            trains.extend([train for train in tg.trains])

        ocps = set()
        ocps.update([train.train_part.first_ocp.ocp.code for train in trains])

        return ocps

    def get_train_cycles(self, wait_time=datetime.timedelta(minutes=5)):
        train_cycles = TrainCycle.get_train_cycles(
            timetableline_id=self.id,
            wait_time=wait_time
        )

        return train_cycles

    def get_one_train_cycle(self, wait_time=datetime.timedelta(minutes=5)):
        """
        gets the first two trains of one train_cycle
        :return:
        """
        train_cycles = TrainCycle.get_train_cycles(
            timetableline_id=self.id,
            wait_time=wait_time
        )

        for cycle in train_cycles:
            if len(cycle.elements[0:2]) == 2:
                break

        elements = cycle.elements[0:2]
        trains = [element.train for element in elements]

        return trains

    def get_train_cycles_each_starting_ocp(self):
        ocps = self.start_ocps
        all_cycles = self.get_train_cycles()
        train_cycles = []
        for cycle in all_cycles:
            ocp = cycle.elements[0].train.train_part.first_ocp.ocp.code
            if ocp in ocps:
                ocps.remove(ocp)
                if len(cycle.elements) > 1:
                    train_cycles.append(cycle)

        return train_cycles


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
    cost_estimate_actual_891_72 = db.Column(db.Integer)
    cost_estimate_actual_891_11 = db.Column(db.Integer)
    cost_estimate_actual_891_21 = db.Column(db.Integer)
    cost_estimate_actual_861_01 = db.Column(db.Integer)

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
    spent_two_years_previous_891_72 = db.Column(db.Integer)
    spent_two_years_previous_891_11 = db.Column(db.Integer)
    spent_two_years_previous_891_21 = db.Column(db.Integer)
    spent_two_years_previous_861_01 = db.Column(db.Integer)

    allowed_previous_year = db.Column(db.Integer)
    allowed_previous_year_third_parties = db.Column(db.Integer)
    allowed_previous_year_equity = db.Column(db.Integer)
    allowed_previous_year_891_01 = db.Column(db.Integer)
    allowed_previous_year_891_02 = db.Column(db.Integer)
    allowed_previous_year_891_03 = db.Column(db.Integer)
    allowed_previous_year_891_04 = db.Column(db.Integer)
    allowed_previous_year_891_91 = db.Column(db.Integer)
    allowed_previous_year_891_72 = db.Column(db.Integer)
    allowed_previous_year_891_11 = db.Column(db.Integer)
    allowed_previous_year_891_21 = db.Column(db.Integer)
    allowed_previous_year_861_01 = db.Column(db.Integer)

    spending_residues = db.Column(db.Integer)
    spending_residues_891_01 = db.Column(db.Integer)
    spending_residues_891_02 = db.Column(db.Integer)
    spending_residues_891_03 = db.Column(db.Integer)
    spending_residues_891_04 = db.Column(db.Integer)
    spending_residues_891_91 = db.Column(db.Integer)
    spending_residues_891_72 = db.Column(db.Integer)
    spending_residues_891_11 = db.Column(db.Integer)
    spending_residues_891_21 = db.Column(db.Integer)
    spending_residues_861_01 = db.Column(db.Integer)

    year_planned = db.Column(db.Integer)
    year_planned_third_parties = db.Column(db.Integer)
    year_planned_equity = db.Column(db.Integer)
    year_planned_891_01 = db.Column(db.Integer)
    year_planned_891_02 = db.Column(db.Integer)
    year_planned_891_03 = db.Column(db.Integer)
    year_planned_891_04 = db.Column(db.Integer)
    year_planned_891_91 = db.Column(db.Integer)
    year_planned_891_72 = db.Column(db.Integer)
    year_planned_891_11 = db.Column(db.Integer)
    year_planned_891_21 = db.Column(db.Integer)
    year_planned_861_01 = db.Column(db.Integer)

    next_years = db.Column(db.Integer)
    next_years_third_parties = db.Column(db.Integer)
    next_years_equity = db.Column(db.Integer)
    next_years_891_01 = db.Column(db.Integer)
    next_years_891_02 = db.Column(db.Integer)
    next_years_891_03 = db.Column(db.Integer)
    next_years_891_04 = db.Column(db.Integer)
    next_years_891_91 = db.Column(db.Integer)
    next_years_891_72 = db.Column(db.Integer)
    next_years_891_11 = db.Column(db.Integer)
    next_years_891_21 = db.Column(db.Integer)
    next_years_861_01 = db.Column(db.Integer)

    finve = db.relationship("FinVe", backref=db.backref("budgets"))
    db.Index('budgets_year_and_finve_uindex', budget_year, fin_ve, unique=True)


class FinVe(db.Model):
    """
    FinVe = Finanzierungsvereinbarung
    a agreement between the state of germany and the infrastructure company to finance infrastructure. It's a little complicated
    """
    __tablename__ = 'finve'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, server_default="2000")
    name = db.Column(db.String(1000))
    starting_year = db.Column(db.Integer)
    cost_estimate_original = db.Column(db.Integer)
    temporary_finve_number = db.Column(db.Boolean, default=False)  # if true the finve number is not known yet

    project_contents = db.relationship('ProjectContent', secondary=finve_to_projectcontent,
                                       backref=db.backref('finve', lazy=True))


class Text(db.Model):
    __tablename__ = 'texts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    header = db.Column(db.String(1000))
    weblink = db.Column(db.String(1000))
    text = db.Column(db.Text)
    type = db.Column(db.Integer, db.ForeignKey('text_types.id'))
    logo_url = db.Column(db.String(1000))

    created_timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # relationship
    text_type = db.relationship('TextType', backref='texts', lazy=True)


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
    polygon = db.Column(geoalchemy2.Geometry(geometry_type='MULTIPOLYGON', srid=4326), nullable=True)

    @property
    def polygon_as_geojson(self):
        polygon = shapely.wkb.loads(self.polygon.desc, hex=True)
        polygon_transformed = shapely.geometry.mapping(polygon)["coordinates"]
        polygon_json = geojson.MultiPolygon(polygon_transformed)
        return polygon_json


class Counties(db.Model):
    """
    Counties (Kreis)
    """
    __tablenmae__ = 'counties'
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
    __tablename__ = 'constituencies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    polygon = db.Column(geoalchemy2.Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey('states.id'))


class MasterScenario(db.Model):
    """
    Manages the scenarios for the master thesis.
    """
    __tablename__ = 'master_scenarios'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    start_year = db.Column(db.Integer, default=2030)
    operation_duration = db.Column(db.Integer, default=30)

    count_area_sum = db.Column(db.Integer)
    count_area_diesel = db.Column(db.Integer)
    count_area_efuel = db.Column(db.Integer)
    count_area_h2 = db.Column(db.Integer)
    count_area_battery = db.Column(db.Integer)
    count_area_electrification = db.Column(db.Integer)
    count_area_optimised_electrification = db.Column(db.Integer)
    count_area_oe_to_battery = db.Column(db.Integer)
    count_area_oe_to_electrification = db.Column(db.Integer)

    infrastructure_km_sum = db.Column(db.Integer)
    infrastructure_km_diesel = db.Column(db.Integer)
    infrastructure_km_efuel = db.Column(db.Integer)
    infrastructure_km_h2 = db.Column(db.Integer)
    infrastructure_km_battery = db.Column(db.Integer)
    infrastructure_km_electrification = db.Column(db.Integer)
    infrastructure_km_optimised_electrification = db.Column(db.Integer)
    infrastructure_km_oe_to_battery = db.Column(db.Integer)
    infrastructure_km_oe_to_electrification = db.Column(db.Integer)

    running_km_sum = db.Column(db.Integer)
    running_km_diesel = db.Column(db.Integer)
    running_km_efuel = db.Column(db.Integer)
    running_km_h2 = db.Column(db.Integer)
    running_km_battery = db.Column(db.Integer)
    running_km_electrification = db.Column(db.Integer)
    running_km_optimised_electrification = db.Column(db.Integer)
    running_km_oe_to_battery = db.Column(db.Integer)
    running_km_oe_to_electrification = db.Column(db.Integer)

    infrastructure_cost_sum = db.Column(db.Integer)
    infrastructure_cost_diesel = db.Column(db.Integer)
    infrastructure_cost_efuel = db.Column(db.Integer)
    infrastructure_cost_h2 = db.Column(db.Integer)
    infrastructure_cost_battery = db.Column(db.Integer)
    infrastructure_cost_electrification = db.Column(db.Integer)
    infrastructure_cost_optimsed_electrification = db.Column(db.Integer)
    infrastructure_cost_oe_to_battery = db.Column(db.Integer)
    infrastructure_cost_oe_to_electrification = db.Column(db.Integer)

    operating_cost_sum = db.Column(db.Integer)
    operating_cost_diesel = db.Column(db.Integer)
    operating_cost_efuel = db.Column(db.Integer)
    operating_cost_h2 = db.Column(db.Integer)
    operating_cost_battery = db.Column(db.Integer)
    operating_cost_electrification = db.Column(db.Integer)
    operating_cost_optimised_electrification = db.Column(db.Integer)
    operating_cost_oe_to_battery = db.Column(db.Integer)
    operating_cost_oe_to_electrification = db.Column(db.Integer)

    co2_new = db.Column(db.Integer)
    co2_diesel = db.Column(db.Integer)

    project_contents = db.relationship("ProjectContent", secondary=projectcontents_to_masterscenario, backref=db.backref('master_scenario'))
    train_costs = db.relationship("TimetableTrainCost", cascade="all, delete", backref=db.backref('master_scenario'))

    @property
    def main_areas(self):
        """
        returns all areas that are no subarea
        :return:
        """
        areas = MasterArea.query.filter(
            MasterArea.scenario_id == self.id,
            MasterArea.superior_master_id == None
        ).all()
        return areas

    def create_areas(self, infra_version):
        """
        Create the areas for one scenario. One Area consists of all lines in an scope, that drive on infrastructure
        having no catenary
        :param infra_version:
        :return:
        """

        # get the railwaylines that have no catenary (for that scenario)
        railwayline_no_catenary = infra_version.get_railwayline_no_catenary()

        # get all sgv_lines, that have no catenary (for that scenario)
        traingroups_no_catenary = db.session.query(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(
            RouteTraingroup).join(TimetableCategory).join(RailwayLine).filter(
            sqlalchemy.and_(
                RailwayLine.id.in_(railwayline_no_catenary),
                RouteTraingroup.master_scenario_id == self.id,
            )).all()

        # a list that contains the collected traingroups
        area_objects = []

        while traingroups_no_catenary:
            area, railwayline_no_catenary, traingroups_no_catenary = self.__search_connected_rw_lines(
                traingroups_no_catenary=traingroups_no_catenary,
                railwayline_no_catenary=railwayline_no_catenary
            )
            area_objects.append(area)

        db.session.add_all(area_objects)
        db.session.commit()

        return area_objects

    def __search_connected_rw_lines(self, traingroups_no_catenary, railwayline_no_catenary):
        # take the first traingroup of the list and remove it from the list. Get also the railway_lines of that traingroup
        traingroups = list()
        rw_lines = list()
        sgv_line = traingroups_no_catenary.pop(0)
        traingroups.append(sgv_line)

        # search for all lines that share a unelectrified railway_line witht the sgv_line
        delta_traingroups = True
        while delta_traingroups is True:
            # get all railwaylines that are used by the traingroups
            rl_lines_additional = db.session.query(RailwayLine).join(RouteTraingroup).join(
                TimetableTrainGroup).filter(
                sqlalchemy.and_(
                    RailwayLine.id.in_(railwayline_no_catenary),
                    TimetableTrainGroup.id.in_([t.id for t in traingroups]),
                    RailwayLine.id.notin_([r.id for r in rw_lines]),
                    RouteTraingroup.master_scenario_id == self.id
                )).all()

            stations = db.session.query(RailwayStation).join(RailwayPoint).join(RailwayNodes).join(RailwayLine, sqlalchemy.or_(
                    RailwayLine.end_node == RailwayNodes.id, RailwayLine.start_node == RailwayNodes.id)).join(
                RouteTraingroup).join(TimetableTrainGroup).filter(
                sqlalchemy.and_(
                    RailwayLine.id.in_(railwayline_no_catenary),
                    TimetableTrainGroup.id.in_([t.id for t in traingroups]),
                    RailwayLine.id.notin_([r.id for r in rw_lines]),
                    RouteTraingroup.master_scenario_id == self.id
                )
            ).all()

            if rl_lines_additional:
                rw_lines = rw_lines + rl_lines_additional

            if len(stations) > 0:
                rl_lines_additional = db.session.query(RailwayLine).join(RouteTraingroup).join(TimetableTrainGroup).join(RailwayNodes, sqlalchemy.or_(
                        RailwayLine.end_node == RailwayNodes.id, RailwayLine.start_node == RailwayNodes.id)).join(
                    RailwayPoint).join(RailwayStation).filter(
                    sqlalchemy.and_(
                        RailwayStation.id.in_([s.id for s in stations]),
                        RailwayLine.id.in_(railwayline_no_catenary),
                        RouteTraingroup.master_scenario_id == self.id,
                        RailwayLine.id.notin_([r.id for r in rw_lines]),
                    )).all()
                if rl_lines_additional:
                    rw_lines = rw_lines + rl_lines_additional

            traingroups_additional = db.session.query(TimetableTrainGroup).join(RouteTraingroup).join(
                RailwayLine).filter(
                sqlalchemy.and_(
                    RailwayLine.id.in_(railwayline_no_catenary),
                    RailwayLine.id.in_([r.id for r in rw_lines]),
                    TimetableTrainGroup.id.notin_([t.id for t in traingroups]),
                    RouteTraingroup.master_scenario_id == self.id
                )).all()

            if traingroups_additional:
                traingroups = traingroups + traingroups_additional
            else:
                delta_traingroups = False

        # Remove used traingroup from traingroups no catenary
        for tg in traingroups:
            if tg in traingroups_no_catenary:
                traingroups_no_catenary.remove(tg)

        # add the traingroups as a collected group to the traingroup_cluster
        area = MasterArea()
        area.scenario_id = self.id
        area.traingroups = traingroups
        area.railway_lines = rw_lines
        return area, railwayline_no_catenary, traingroups_no_catenary

    def delete_areas(self):
        areas = self.master_areas
        pc_delete = []
        for area in areas:
            area.traingroups = []
            area.railway_lines = []
            pc_delete.extend(area.project_contents)
            area.project_contents = []
            # area.traction_optimised_electrification = []
            # for traction in area.traction_optimised_electrification:
            #     db.session.delete(traction)

        for pc in pc_delete:
            db.session.delete(pc)

        for area in areas:
            db.session.delete(area)

        db.session.commit()

    def route_traingroups(self, infra_version):
        """
        routes the traingroups for this scenario
        :param infra_version:
        :return:
        """
        from prosd.graph import railgraph, routing
        rg = railgraph.RailGraph()
        graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
        route = routing.GraphRoute(graph=graph, infra_version=infra_version)

        traingroups_route = db.session.query(TimetableTrainGroup).filter(
            ~sqlalchemy.exists().where(
                sqlalchemy.and_(
                    RouteTraingroup.traingroup_id == TimetableTrainGroup.id,
                    RouteTraingroup.master_scenario_id == infra_version.scenario.id
                )
            )
        ).all()

        for tg in traingroups_route:
            try:
                route.line(traingroup=tg, force_recalculation=False)
            except (UnboundLocalError, networkx.exception.NodeNotFound) as e:
                logging.error(f"{e.args} {tg}")

    def calc_cost_all_tractions(self, infra_version):

        if parameter.REROUTE_TRAINGROUP:
            self.route_traingroups(infra_version=infra_version)
        if parameter.DELETE_AREAS:
            self.delete_areas()
        if parameter.CREATE_AREAS:
            self.create_areas(infra_version=infra_version)

        areas = MasterArea.query.filter(
            MasterArea.scenario_id == self.id,
            MasterArea.superior_master_area == None
        ).all()

        for area in areas:
            logging.info(f"calculation {area} started")
            area.calculate_cost(infra_version=infra_version, overwrite_infrastructure=parameter.OVERWRITE_INFRASTRUCTURE)

    def calc_cost_one_traction(self, traction, infra_version):
        areas = MasterArea.query.filter(
            MasterArea.scenario_id == self.id,
            MasterArea.superior_master_area == None
        ).all()

        for area in areas:
            logging.info(f"calculation {area} started")
            area.calculate_infrastructure_cost(traction=traction, infra_version=infra_version, overwrite=parameter.OVERWRITE_INFRASTRUCTURE)
            area.calc_operating_cost(
                traction=traction,
                infra_version=infra_version,
                order_calculation_methods=None,
                traingroup_to_traction=None,
                overwrite=False
            )

    def calc_operating_cost_one_traction(self, traction, infra_version, overwrite_operating_cost):
        areas = MasterArea.query.filter(
            MasterArea.scenario_id == self.id,
            MasterArea.superior_master_area == None
        ).all()

        for area in areas:
            area.calc_operating_cost(
                traction=traction,
                infra_version=infra_version,
                order_calculation_methods=None,
                traingroup_to_traction=None,
                overwrite=overwrite_operating_cost
            )

    def calc_infrastructure_cost_one_traction(self, traction, infra_version, overwrite=parameter.OVERWRITE_INFRASTRUCTURE):
        areas = self.main_areas
        for area in areas:
            if 'sgv' in area.categories and (traction == 'battery' or traction == 'h2'):
                continue
            area.calculate_infrastructure_cost(
                traction=traction, infra_version=infra_version, overwrite=overwrite
            )

    @property
    def parameters(self):
        parameters = dict()
        cost_effective_traction = {traction: {"area": 0, "infra_km": 0, "running_km": 0, "infrastructure_cost": 0, "operating_cost": 0} for traction in parameter.TRACTIONS}
        cost_effective_traction_no_optimised = {traction: {"area": 0, "infra_km": 0, "running_km": 0, "infrastructure_cost": 0, "operating_cost": 0} for traction in parameter.TRACTIONS}
        cost_effective_traction_no_optimised.pop('optimised_electrification', None)

        cost_effective_traction["no calculated cost"] = {"area":0, "infra_km": 0, "running_km": 0, "infrastructure_cost": 0, "operating_cost": 0}
        cost_effective_traction_no_optimised["no calculated cost"] = {"area":0, "infra_km": 0, "running_km": 0, "infrastructure_cost": 0, "operating_cost": 0}

        cost_sum_infrastructure = 0
        cost_sum_operating = 0
        running_km_sum = 0
        co2_diesel = 0
        co2_new = 0

        running_km_by_transport_mode = {
            "spnv": {"battery": 0, "electrification": 0, "diesel": 0, "efuel": 0, "h2": 0},
            "spfv": {"battery": 0, "electrification": 0, "diesel": 0, "efuel": 0, "h2": 0},
            "sgv": {"battery": 0, "electrification": 0, "diesel": 0, "efuel": 0, "h2": 0},
            "all": {"battery": 0, "electrification": 0, "diesel": 0, "efuel": 0, "h2": 0}
        }

        for area in self.main_areas:
            cost_master_area = area.cost_overview
            effective_traction = cost_master_area["minimal_cost"]
            area_running_km_traingroups_by_transport_mode = area.running_km_traingroups_by_transport_mode

            cost_effective_traction[effective_traction]["area"] += 1
            cost_effective_traction[effective_traction]["infra_km"] += area.length/1000
            cost_effective_traction[effective_traction]["running_km"] += area_running_km_traingroups_by_transport_mode["all"]
            cost_effective_traction[effective_traction]["infrastructure_cost"] += cost_master_area["infrastructure_cost"][effective_traction]
            cost_effective_traction[effective_traction]["operating_cost"] += cost_master_area["operating_cost"][effective_traction]

            cost_sum_infrastructure += cost_master_area["infrastructure_cost"][effective_traction]
            cost_sum_operating += cost_master_area["operating_cost"][effective_traction]
            running_km_sum += area_running_km_traingroups_by_transport_mode["all"]

            if effective_traction == 'optimised_electrification':
                # infra_km
                proportion_traction_by_km = area.proportion_traction_optimised_electrification["infrastructure_kilometer"]
                for key, value in proportion_traction_by_km.items():
                    cost_effective_traction_no_optimised[key]["infra_km"] += value

                # infrastructure_cost
                for key, value in area.proportion_traction_optimised_electrification["infrastructure_cost"].items():
                    cost_effective_traction_no_optimised[key]["infrastructure_cost"] += value

                # running_km
                traction_optimised_traingroups = area.traction_optimised_traingroups
                for key, traction in traction_optimised_traingroups.items():
                    tg = TimetableTrainGroup.query.get(key)
                    train_category = tg.category.transport_mode
                    running_km_day = tg.running_km_day(self.id)
                    cost_effective_traction_no_optimised[traction]["running_km"] += running_km_day
                    co2_new += TimetableTrainCost.query.filter(
                        TimetableTrainCost.traingroup_id == key,
                        TimetableTrainCost.master_scenario_id == self.id,
                        TimetableTrainCost.traction == traction
                    ).scalar().co2_emission
                    co2_diesel += TimetableTrainCost.query.filter(
                        TimetableTrainCost.traingroup_id == key,
                        TimetableTrainCost.master_scenario_id == self.id,
                        TimetableTrainCost.traction == 'diesel'
                    ).scalar().co2_emission

                    running_km_by_transport_mode[train_category][traction] += running_km_day
                    running_km_by_transport_mode["all"][traction] += running_km_day

            else:
                cost_effective_traction_no_optimised[effective_traction]["area"] += 1
                cost_effective_traction_no_optimised[effective_traction]["running_km"] += area_running_km_traingroups_by_transport_mode["all"]
                cost_effective_traction_no_optimised[effective_traction]["infra_km"] += area.length/1000
                cost_effective_traction_no_optimised[effective_traction]["infrastructure_cost"] += \
                cost_master_area["infrastructure_cost"][effective_traction]
                cost_effective_traction_no_optimised[effective_traction]["operating_cost"] += cost_master_area["operating_cost"][
                    effective_traction]
                co2_new += area.get_co2_for_traction[effective_traction]
                for transport_mode in ["spnv", "sgv", "spfv", "all"]:
                    running_km_by_transport_mode[transport_mode][effective_traction] += area_running_km_traingroups_by_transport_mode[transport_mode]

        parameters["cost_effective_traction"] = cost_effective_traction
        parameters["cost_effective_traction_no_optimised"] = cost_effective_traction_no_optimised
        parameters["sum_infrastructure"] = cost_sum_infrastructure
        parameters["sum_operating_cost"] = cost_sum_operating
        parameters["running_km_by_transport_mode"] = running_km_by_transport_mode  # Zug-km pro Tag
        parameters["co2_old"] = co2_diesel
        parameters["co2_new"] = co2_new

        return parameters

    def save_parameters(self):
        """
        Calculates the parameters and adds the values to the model in the db
        :return:
        """
        parameters = self.parameters

        self.count_area_diesel = parameters["cost_effective_traction"]["diesel"]["area"]
        self.count_area_efuel = parameters["cost_effective_traction"]["efuel"]["area"]
        self.count_area_h2 = parameters["cost_effective_traction"]["h2"]["area"]
        self.count_area_battery = parameters["cost_effective_traction"]["battery"]["area"]
        self.count_area_electrification = parameters["cost_effective_traction"]["electrification"]["area"]
        self.count_area_optimised_electrification = parameters["cost_effective_traction"]["optimised_electrification"]["area"]
        self.count_area_oe_to_battery = parameters["cost_effective_traction_no_optimised"]["battery"]["area"] - parameters["cost_effective_traction"]["battery"]["area"]
        self.count_area_oe_to_electrification = parameters["cost_effective_traction_no_optimised"]["electrification"]["area"] - parameters["cost_effective_traction"]["electrification"]["area"]
        self.count_area_sum = self.count_area_diesel + self.count_area_efuel + self.count_area_h2 + self.count_area_battery + self.count_area_electrification + self.count_area_optimised_electrification

        self.infrastructure_km_diesel = parameters["cost_effective_traction"]["diesel"]["infra_km"]
        self.infrastructure_km_efuel = parameters["cost_effective_traction"]["efuel"]["infra_km"]
        self.infrastructure_km_h2 = parameters["cost_effective_traction"]["h2"]["infra_km"]
        self.infrastructure_km_battery = parameters["cost_effective_traction"]["battery"]["infra_km"]
        self.infrastructure_km_electrification = parameters["cost_effective_traction"]["electrification"]["infra_km"]
        self.infrastructure_km_optimised_electrification = parameters["cost_effective_traction"]["optimised_electrification"]["infra_km"]
        self.infrastructure_km_oe_to_battery = parameters["cost_effective_traction_no_optimised"]["battery"]["infra_km"] - parameters["cost_effective_traction"]["battery"]["infra_km"]
        self.infrastructure_km_oe_to_electrification = parameters["cost_effective_traction_no_optimised"]["electrification"]["infra_km"] - parameters["cost_effective_traction"]["electrification"]["infra_km"]
        self.infrastructure_km_sum = self.infrastructure_km_diesel + self.infrastructure_km_efuel + self.infrastructure_km_h2 + self.infrastructure_km_battery + self.infrastructure_km_electrification + self.infrastructure_km_optimised_electrification

        self.running_km_diesel = parameters["cost_effective_traction"]["diesel"]["running_km"]
        self.running_km_efuel = parameters["cost_effective_traction"]["efuel"]["running_km"]
        self.running_km_h2 = parameters["cost_effective_traction"]["h2"]["running_km"]
        self.running_km_battery = parameters["cost_effective_traction"]["battery"]["running_km"]
        self.running_km_electrification = parameters["cost_effective_traction"]["electrification"]["running_km"]
        self.running_km_optimised_electrification = parameters["cost_effective_traction"]["optimised_electrification"]["running_km"]
        self.running_km_oe_to_battery = parameters["cost_effective_traction_no_optimised"]["battery"]["running_km"] - parameters["cost_effective_traction"]["battery"]["running_km"]
        self.running_km_oe_to_electrification = parameters["cost_effective_traction_no_optimised"]["electrification"]["running_km"] - parameters["cost_effective_traction"]["electrification"]["running_km"]
        self.running_km_sum = self.running_km_diesel + self.running_km_efuel + self.running_km_h2 + self.running_km_battery + self.running_km_electrification + self.running_km_optimised_electrification

        self.infrastructure_cost_diesel = parameters["cost_effective_traction"]["diesel"]["infrastructure_cost"]
        self.infrastructure_cost_efuel = parameters["cost_effective_traction"]["efuel"]["infrastructure_cost"]
        self.infrastructure_cost_h2 = parameters["cost_effective_traction"]["h2"]["infrastructure_cost"]
        self.infrastructure_cost_battery = parameters["cost_effective_traction"]["battery"]["infrastructure_cost"]
        self.infrastructure_cost_electrification = parameters["cost_effective_traction"]["electrification"]["infrastructure_cost"]
        self.infrastructure_cost_optimsed_electrification = parameters["cost_effective_traction"]["optimised_electrification"]["infrastructure_cost"]
        self.infrastructure_cost_oe_to_battery = parameters["cost_effective_traction_no_optimised"]["battery"]["infrastructure_cost"] - parameters["cost_effective_traction"]["battery"]["infrastructure_cost"]
        self.infrastructure_cost_oe_to_electrification = parameters["cost_effective_traction_no_optimised"]["electrification"]["infrastructure_cost"] - parameters["cost_effective_traction"]["electrification"]["infrastructure_cost"]
        self.infrastructure_cost_sum = parameters["sum_infrastructure"]

        self.operating_cost_diesel = parameters["cost_effective_traction"]["diesel"]["operating_cost"]
        self.operating_cost_efuel = parameters["cost_effective_traction"]["efuel"]["operating_cost"]
        self.operating_cost_h2 = parameters["cost_effective_traction"]["h2"]["operating_cost"]
        self.operating_cost_battery = parameters["cost_effective_traction"]["battery"]["operating_cost"]
        self.operating_cost_electrification = parameters["cost_effective_traction"]["electrification"]["operating_cost"]
        self.operating_cost_optimised_electrification = parameters["cost_effective_traction"]["optimised_electrification"]["operating_cost"]
        self.operating_cost_oe_to_battery = parameters["cost_effective_traction_no_optimised"]["battery"]["operating_cost"] - parameters["cost_effective_traction"]["battery"]["operating_cost"]
        self.operating_cost_oe_to_electrification = parameters["cost_effective_traction_no_optimised"]["electrification"]["operating_cost"] - parameters["cost_effective_traction"]["electrification"]["operating_cost"]
        self.operating_cost_sum = parameters["sum_operating_cost"]

        self.co2_new = parameters["co2_new"]
        self.co2_diesel = parameters["co2_old"]

        db.session.add(self)
        db.session.commit()


class MasterArea(db.Model):
    """
    the areas in which the scenario is divided
    """
    __tablename__ = 'master_areas'
    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('master_scenarios.id', onupdate='CASCADE', ondelete='CASCADE'))
    superior_master_id = db.Column(db.Integer, db.ForeignKey('master_areas.id', onupdate='CASCADE', ondelete='CASCADE'))

    traction_minimal_cost = db.Column(db.String(255))

    cost_efuel = db.Column(db.Integer)
    cost_diesel = db.Column(db.Integer)
    cost_h2 = db.Column(db.Integer)
    cost_battery = db.Column(db.Integer)
    cost_electrification = db.Column(db.Integer)
    cost_optimised_electrification = db.Column(db.Integer)

    operating_cost_efuel = db.Column(db.Integer)
    operating_cost_diesel = db.Column(db.Integer)
    operating_cost_h2 = db.Column(db.Integer)
    operating_cost_battery = db.Column(db.Integer)
    operating_cost_electrification = db.Column(db.Integer)
    operating_cost_optimised_electrification = db.Column(db.Integer)

    infrastructure_cost_efuel = db.Column(db.Integer)
    infrastructure_cost_diesel = db.Column(db.Integer)
    infrastructure_cost_h2 = db.Column(db.Integer)
    infrastructure_cost_battery = db.Column(db.Integer)
    infrastructure_cost_electrification = db.Column(db.Integer)
    infrastructure_cost_optimised_electrification = db.Column(db.Integer)

    sgv = db.Column(db.Boolean, default=False)
    spnv = db.Column(db.Boolean, default=False)
    spfv = db.Column(db.Boolean, default=False)

    traingroups = db.relationship("TimetableTrainGroup", secondary=traingroups_to_masterareas, backref=db.backref('master_areas', lazy=True))
    railway_lines = db.relationship("RailwayLine", secondary=railwaylines_to_masterareas, backref=db.backref('master_areas', lazy=True))
    project_contents = db.relationship("ProjectContent", secondary=projectcontents_to_masterareas, backref=db.backref('master_areas'))
    scenario = db.relationship("MasterScenario", backref=db.backref('master_areas'))
    superior_master_area = db.relationship('MasterArea', remote_side=[id], backref=db.backref('sub_master_areas'))
    traction_optimised_electrification = db.relationship("TractionOptimisedElectrification", cascade="all, delete", backref="masterarea")

    @property
    def categories(self):
        categories = db.session.query(TimetableCategory.transport_mode).join(TimetableTrainPart).join(TimetableTrain).join(TimetableTrainGroup).join(traingroups_to_masterareas).join(MasterArea).filter(MasterArea.id == self.id).group_by(TimetableCategory.transport_mode).all()
        categories = [category[0] for category in categories]

        return categories

    @property
    def length(self):
        length_lines = [line.length for line in self.railway_lines]
        length = sum(length_lines)
        return length  # in meter

    @property
    def traction_optimised_traingroups(self):
        tractions = TractionOptimisedElectrification.query.filter(
            TractionOptimisedElectrification.master_area_id == self.id
        ).all()

        traction_optimised_traingroups = {traction.traingroup_id:traction.traction for traction in tractions}

        return traction_optimised_traingroups

    @property
    def running_km_traingroups_by_transport_mode(self):
        running_km_traingroups_by_transport_mode = {
            "sgv": 0,
            "spnv": 0,
            "spfv": 0,
            "all": 0
        }

        running_km_tgs = db.session.query(TimetableTrainGroup, sqlalchemy.func.sum(RailwayLine.length),
                         sqlalchemy.func.count(sqlalchemy.distinct(TimetableTrain.id))).join(
            RouteTraingroup, RouteTraingroup.railway_line_id == RailwayLine.id).join(
            TimetableTrainGroup, TimetableTrainGroup.id == RouteTraingroup.traingroup_id).join(
            TimetableTrain, TimetableTrain.train_group_id == TimetableTrainGroup.id).filter(
            RouteTraingroup.traingroup_id.in_([tg.id for tg in self.traingroups]),
            RouteTraingroup.master_scenario_id == self.scenario_id
        ).group_by(TimetableTrainGroup.id).all()

        for tg in running_km_tgs:
            running_km_traingroups_by_transport_mode[tg[0].category.transport_mode] += tg[1]/1000
            running_km_traingroups_by_transport_mode["all"] += tg[1]/1000

        return running_km_traingroups_by_transport_mode

    def _calc_running_km_traingroup(self, tg):
        running_km_traingroup = tg.running_km_day(self.scenario_id)
        transport_mode = tg.category.transport_mode
        return running_km_traingroup, transport_mode

    @hybrid_method
    def get_operating_cost_traction(self, traction):
        """
        get the operating cost for one traction
        :param traction:
        :return:
        """
        train_cost = 0
        if traction == 'optimised_electrification':
            traingroup_traction = self.traction_optimised_traingroups

            traingroups_spnv_costs = db.session.query(TimetableTrainCost.traingroup_id, TimetableTrainCost.traction, TimetableTrainCost.cost).filter(
                TimetableTrainCost.traingroup_id.in_(
                    db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(
                        TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                        MasterArea.id == self.id,
                        TimetableCategory.transport_mode == 'spnv'
                    ).group_by(TimetableTrainGroup.id)),
                TimetableTrainCost.master_scenario_id == self.scenario_id,
                TimetableTrainCost.calculation_method == 'standi',
                TimetableTrainCost.traction.in_(['battery','electrification'])
            ).all()
            traingroups_spnv_costs = {tg[0]+'_'+tg[1]:tg[2] for tg in traingroups_spnv_costs}

            traingroups_spfv_costs = db.session.query(TimetableTrainCost.traingroup_id, TimetableTrainCost.traction,
                                                      TimetableTrainCost.cost).filter(
                TimetableTrainCost.traingroup_id.in_(
                    db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(
                        TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                        MasterArea.id == self.id,
                        TimetableCategory.transport_mode == 'spfv'
                    ).group_by(TimetableTrainGroup.id)),
                TimetableTrainCost.master_scenario_id == self.scenario_id,
                TimetableTrainCost.calculation_method == 'standi',
                TimetableTrainCost.traction.in_(['battery', 'electrification'])
            ).all()
            traingroups_spfv_costs = {tg[0] + '_' + tg[1]: tg[2] for tg in traingroups_spfv_costs}

            traingroups_sgv_costs = db.session.query(TimetableTrainCost.traingroup_id, TimetableTrainCost.traction,
                                                      TimetableTrainCost.cost).filter(
                TimetableTrainCost.traingroup_id.in_(
                    db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(
                        TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                        MasterArea.id == self.id,
                        TimetableCategory.transport_mode == 'sgv'
                    ).group_by(TimetableTrainGroup.id)),
                TimetableTrainCost.master_scenario_id == self.scenario_id,
                TimetableTrainCost.calculation_method == 'bvwp',
                TimetableTrainCost.traction.in_(['battery', 'electrification'])
            ).all()
            traingroups_sgv_costs = {tg[0] + '_' + tg[1]: tg[2] for tg in traingroups_sgv_costs}
            traingroups_costs = dict()
            traingroups_costs.update(traingroups_spnv_costs)
            traingroups_costs.update(traingroups_sgv_costs)
            traingroups_costs.update(traingroups_spfv_costs)

            for tg_id, traction in traingroup_traction.items():
                train_cost += traingroups_costs[tg_id+'_'+traction]

        else:
            train_cost_spnv = db.session.query(TimetableTrainCost.cost).filter(
                                    TimetableTrainCost.traingroup_id.in_(
                                        db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                                            MasterArea.id == self.id,
                                            TimetableCategory.transport_mode == 'spnv'
                                        )
                                    ),
                                    TimetableTrainCost.master_scenario_id == self.scenario_id,
                                    TimetableTrainCost.calculation_method == 'standi',
                                    TimetableTrainCost.traction == traction
                                ).all()
            train_cost_spnv_sum = sum([tg[0] for tg in train_cost_spnv])
            train_cost_sgv = db.session.query(TimetableTrainCost.cost).filter(
                                    TimetableTrainCost.traingroup_id.in_(
                                        db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                                            MasterArea.id == self.id,
                                            TimetableCategory.transport_mode == 'sgv'
                                        )
                                    ),
                                    TimetableTrainCost.master_scenario_id == self.scenario_id,
                                    TimetableTrainCost.calculation_method == 'bvwp',
                                    TimetableTrainCost.traction == traction
                                ).all()
            train_cost_sgv_sum = sum([tg[0] for tg in train_cost_sgv])
            train_cost_spfv = db.session.query(TimetableTrainCost.cost).filter(
                                    TimetableTrainCost.traingroup_id.in_(
                                        db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                                            MasterArea.id == self.id,
                                            TimetableCategory.transport_mode == 'spfv'
                                        )
                                    ),
                                    TimetableTrainCost.master_scenario_id == self.scenario_id,
                                    TimetableTrainCost.calculation_method == 'standi',
                                    TimetableTrainCost.traction == traction
                                ).all()
            train_cost_spfv_sum = sum([tg[0] for tg in train_cost_spfv])
            train_cost = train_cost_spfv_sum + train_cost_sgv_sum + train_cost_spnv_sum

        train_cost_base_year = BaseCalculation().cost_base_year(start_year=parameter.START_YEAR,
                                                                duration=parameter.DURATION_OPERATION, cost=train_cost,
                                                                cost_is_sum=False)

        return train_cost_base_year

    @property
    def operating_cost_all_tractions(self):
        """
        Get the operating cost for all tractions
        :return:
        """
        train_cost_spnv = db.session.query(TimetableTrainCost.traction,
                                           sqlalchemy.func.sum(TimetableTrainCost.cost)).filter(
            TimetableTrainCost.traingroup_id.in_(
                db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(
                    TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                    MasterArea.id == self.id,
                    TimetableCategory.transport_mode == 'spnv'
                )
            ),
            TimetableTrainCost.master_scenario_id == self.scenario_id,
            TimetableTrainCost.calculation_method == 'standi'
        ).group_by(TimetableTrainCost.traction).all()
        train_cost_spnv = {traction[0]: traction[1] for traction in train_cost_spnv}
        train_cost_sgv = db.session.query(TimetableTrainCost.traction,
                                          sqlalchemy.func.sum(TimetableTrainCost.cost)).filter(
            TimetableTrainCost.traingroup_id.in_(
                db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(
                    TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                    MasterArea.id == self.id,
                    TimetableCategory.transport_mode == 'sgv'
                )
            ),
            TimetableTrainCost.master_scenario_id == self.scenario_id,
            TimetableTrainCost.calculation_method == 'bvwp'
        ).group_by(TimetableTrainCost.traction).all()
        train_cost_sgv = {traction[0]: traction[1] for traction in train_cost_sgv}
        train_cost_spfv = db.session.query(TimetableTrainCost.traction,
                                           sqlalchemy.func.sum(TimetableTrainCost.cost)).filter(
            TimetableTrainCost.traingroup_id.in_(
                db.session.query(TimetableTrainGroup.id).join(traingroups_to_masterareas).join(MasterArea).join(
                    TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                    MasterArea.id == self.id,
                    TimetableCategory.transport_mode == 'spfv'
                )
            ),
            TimetableTrainCost.master_scenario_id == self.scenario_id,
            TimetableTrainCost.calculation_method == 'standi'
        ).group_by(TimetableTrainCost.traction).all()
        train_cost_spfv = {traction[0]: traction[1] for traction in train_cost_spfv}

        train_costs = dict()
        for traction in parameter.TRACTIONS:
            if 'sgv' in self.categories and (traction == "battery" or traction == "h2"):
                continue
            if traction == 'optimised_electrification':
                train_costs[traction] = self.get_operating_cost_traction(traction='optimised_electrification')
            else:
                train_cost_traction_year = 0
                if traction in train_cost_spnv.keys():
                    train_cost_traction_year += train_cost_spnv[traction]
                if traction in train_cost_sgv.keys():
                    train_cost_traction_year += train_cost_sgv[traction]
                if traction in train_cost_spfv.keys():
                    train_cost_traction_year += train_cost_spfv[traction]

                train_costs[traction] = BaseCalculation().cost_base_year(start_year=parameter.START_YEAR,
                                                                duration=parameter.DURATION_OPERATION, cost=train_cost_traction_year,
                                                                cost_is_sum=False)

        return train_costs

    @property
    def infrastructure_cost_all_tractions(self):
        """
        returns a dictionary that contents the project_contents for each traction
        :return:
        """
        cost_by_traction = dict()

        for pc in self.project_contents:
            if pc.elektrification is True:
                cost_by_traction["electrification"] = pc.planned_total_cost
            elif pc.battery is True:
                cost_by_traction["battery"] = pc.planned_total_cost
            elif pc.optimised_electrification is True:
                cost_by_traction["optimised_electrification"] = pc.planned_total_cost
            elif pc.filling_stations_h2 is True:
                cost_by_traction["h2"] = pc.planned_total_cost
            elif pc.filling_stations_efuel is True:
                cost_by_traction["efuel"] = pc.planned_total_cost
            elif pc.filling_stations_diesel is True:
                cost_by_traction["diesel"] = pc.planned_total_cost

        return cost_by_traction

    @hybrid_method
    def cost_traction(self, traction):
        """
        get infrastructure cost and operating cost for one traction
        """
        cost_traction = self.get_operating_cost_traction(traction) + self.infrastructure_cost_all_tractions[traction]

        return cost_traction

    @property
    def cost_all_tractions(self):
        """
        the complete costs for all tractions
        includes infrastructure and operating costs
        :return:
        """
        cost_tractions = dict()
        infrastructure_cost = self.infrastructure_cost_all_tractions
        train_cost = self.operating_cost_all_tractions

        for traction in tractions:
            try:
                cost_tractions[traction] = infrastructure_cost[traction] + train_cost[traction]
            except KeyError as e:
                logging.info(f"No infrastructure cost or train_cost for {self.id} {e}")

        return cost_tractions

    @property
    def get_co2_for_traction(self):
        values = db.session.query(TimetableTrainCost.traction, sqlalchemy.func.sum(TimetableTrainCost.co2_emission)).filter(
            TimetableTrainCost.traingroup_id.in_([tg.id for tg in self.traingroups]),
            TimetableTrainCost.master_scenario_id == self.scenario_id
        ).group_by(TimetableTrainCost.traction).all()
        co2_tractions = {value[0]:value[1] for value in values}

        # optimised electrification gets calculated separated
        co2_optimised_electrification = 0
        traction_optimised_traingroups = self.traction_optimised_traingroups
        train_emissions = db.session.query(TimetableTrainCost.traingroup_id, TimetableTrainCost.traction, TimetableTrainCost.co2_emission).filter(
            TimetableTrainCost.traingroup_id.in_([tg.id for tg in self.traingroups]),
            TimetableTrainCost.master_scenario_id == self.scenario_id,
            TimetableTrainCost.traction.in_(['battery','electrification'])
        ).all()
        train_emissions = {tg[0]+'_'+tg[1]:tg[2] for tg in train_emissions}
        for tg, traction in traction_optimised_traingroups.items():
            co2_optimised_electrification+=train_emissions[tg+'_'+traction]

        co2_tractions["optimised_electrification"] = co2_optimised_electrification

        return co2_tractions

    @property
    def get_operating_cost_categories_by_transport_mode(self):
        transport_modes = {
            'sgv': ['sgv'],
            'spfv': ['spfv'],
            'spnv': ['spnv'],
            'all': ['sgv', 'spfv', 'spnv']
        }
        train_costs_transport_mode = dict()

        for name_transport_mode, transport_mode in transport_modes.items():
            train_costs_traction = dict()
            traingroups = TimetableTrainGroup.query.join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
                TimetableTrainGroup.id.in_([tg.id for tg in self.traingroups]),
                TimetableCategory.transport_mode.in_(transport_mode)
            ).all()

            if len(traingroups) == 0:
                continue

            train_costs = db.session.query(TimetableTrainCost.traction.label('traction'), sqlalchemy.func.sum(TimetableTrainCost.cost).label('train_cost'),
                             sqlalchemy.func.sum(TimetableTrainCost.debt_service).label('debt_service'),
                             sqlalchemy.func.sum(TimetableTrainCost.maintenance_cost).label('maintenance_cost'),
                             sqlalchemy.func.sum(TimetableTrainCost.energy_cost).label('energy_cost'),
                             sqlalchemy.func.sum(TimetableTrainCost.co2_cost).label('co2_cost'),
                             sqlalchemy.func.sum(TimetableTrainCost.pollutants_cost).label('pollutants_cost'),
                             sqlalchemy.func.sum(TimetableTrainCost.primary_energy_cost).label('primary_energy_cost'),
                             sqlalchemy.func.sum(TimetableTrainCost.co2_emission).label('co2_emission'),
                             sqlalchemy.func.sum(TimetableTrainCost.thg_vehicle_production_cost).label('thg_vehicle_production_cost')).filter(
                TimetableTrainCost.traingroup_id.in_([tg.id for tg in traingroups]),
                TimetableTrainCost.master_scenario_id == self.scenario_id
            ).group_by(TimetableTrainCost.traction).all()

            for row in train_costs:
                mapped_row = row._mapping
                traction = mapped_row['traction']
                row_as_dict = dict(row._mapping)
                if row_as_dict["thg_vehicle_production_cost"] is None:
                    row_as_dict["thg_vehicle_production_cost"] = 0
                row_as_dict.pop('traction')
                train_costs_traction[traction] = row_as_dict

            train_costs_traction["optimised_electrification"] = {}
            for tg_id, traction in self.traction_optimised_traingroups.items():
                if TimetableTrainGroup.query.get(tg_id).category.transport_mode not in transport_mode:
                    continue
                train_costs = db.session.query(TimetableTrainCost.cost.label('train_cost'),
                                               TimetableTrainCost.debt_service.label('debt_service'),
                                               TimetableTrainCost.maintenance_cost.label(
                                                   'maintenance_cost'),
                                               TimetableTrainCost.energy_cost.label('energy_cost'),
                                               TimetableTrainCost.co2_cost.label('co2_cost'),
                                               TimetableTrainCost.pollutants_cost.label(
                                                   'pollutants_cost'),
                                               TimetableTrainCost.primary_energy_cost.label(
                                                   'primary_energy_cost'),
                                               TimetableTrainCost.co2_emission.label('co2_emission'),
                                               TimetableTrainCost.thg_vehicle_production_cost.label(
                                                   'thg_vehicle_production_cost')).filter(
                                                TimetableTrainCost.traingroup_id == tg_id,
                                                TimetableTrainCost.traction == traction,
                                                TimetableTrainCost.master_scenario_id == self.scenario_id,
                                                ).all()

                row_as_dict = dict(train_costs[0]._mapping)
                for key, value in row_as_dict.items():
                    if value is None:
                        logging.debug(f"For area {self.id} operational cost factor {key} for traction {traction} for {tg_id} has value {value}. Value is set to 0")  # normal for sgv
                        value = 0
                    if key in train_costs_traction["optimised_electrification"]:
                        train_costs_traction["optimised_electrification"][key] += value
                    else:
                        train_costs_traction["optimised_electrification"][key] = value

            train_costs_transport_mode[name_transport_mode] = train_costs_traction

        return train_costs_transport_mode

    @property
    def cost_overview(self):
        """
        collects all that stuff in one dict -> better for api
        :return:
        """
        cost_dict = {}
        cost_dict["infrastructure_cost"] = self.infrastructure_cost_all_tractions
        cost_dict["operating_cost"] = self.operating_cost_all_tractions

        cost_dict["co2"] = {}
        cost_dict["sum_cost"] = {}

        # calculate the sum_cost
        for traction in parameter.TRACTIONS:
            try:
                cost_dict["sum_cost"][traction] = cost_dict["infrastructure_cost"][traction] + cost_dict["operating_cost"][traction]

            except KeyError as e:
                logging.info(f"No infrastructure cost or train_cost for {self.id} {e}")

        # calculate the co2
        co2_traction = self.get_co2_for_traction
        if 'sgv' in self.categories:
            if 'h2' in co2_traction.keys():
                co2_traction.pop('h2')
            if 'battery' in co2_traction.keys():
                co2_traction.pop('battery')
        cost_dict['co2'] = co2_traction

        minimal_cost_traction = min(cost_dict["sum_cost"], key=cost_dict["sum_cost"].get)
        cost_dict["minimal_cost"] = minimal_cost_traction

        return cost_dict

    def save_parameters(self):
        """
        save parameters to the db for quicker usage
        :return:
        """
        cost_overview = self.cost_overview
        categories = self.categories

        if self.superior_master_area is not None:
            self.traction_minimal_cost = cost_overview["minimal_cost"]
            # than only electrification and battery is calculated
            self.cost_electrification = cost_overview["sum_cost"]["electrification"]
            self.operating_cost_electrification = cost_overview["operating_cost"]["electrification"]
            self.infrastructure_cost_electrification = cost_overview["infrastructure_cost"]["electrification"]

            if 'sgv' not in categories:
                self.cost_battery = cost_overview["sum_cost"]["battery"]
                self.operating_cost_battery = cost_overview["operating_cost"]["battery"]
                self.infrastructure_cost_battery = cost_overview["infrastructure_cost"]["battery"]

        else:
            self.traction_minimal_cost = cost_overview["minimal_cost"]
            self.cost_efuel = cost_overview["sum_cost"]["efuel"]
            self.cost_diesel = cost_overview["sum_cost"]["diesel"]
            self.cost_electrification = cost_overview["sum_cost"]["electrification"]
            self.cost_optimised_electrification = cost_overview["sum_cost"]["optimised_electrification"]

            self.operating_cost_efuel = cost_overview["operating_cost"]["efuel"]
            self.operating_cost_diesel = cost_overview["operating_cost"]["diesel"]
            self.operating_cost_electrification = cost_overview["operating_cost"]["electrification"]
            self.operating_cost_optimised_electrification = cost_overview["operating_cost"]["optimised_electrification"]

            self.infrastructure_cost_efuel = cost_overview["infrastructure_cost"]["efuel"]
            self.infrastructure_cost_diesel = cost_overview["infrastructure_cost"]["diesel"]
            self.infrastructure_cost_electrification = cost_overview["infrastructure_cost"]["electrification"]
            self.infrastructure_cost_optimised_electrification = cost_overview["infrastructure_cost"]["optimised_electrification"]

            if 'sgv' not in categories:
                self.cost_h2 = cost_overview["sum_cost"]["h2"]
                self.cost_battery = cost_overview["sum_cost"]["battery"]
                self.operating_cost_h2 = cost_overview["operating_cost"]["h2"]
                self.operating_cost_battery = cost_overview["operating_cost"]["battery"]
                self.infrastructure_cost_h2 = cost_overview["infrastructure_cost"]["h2"]
                self.infrastructure_cost_battery = cost_overview["infrastructure_cost"]["battery"]

        # add categories that are used in that master area
        if 'sgv' in categories:
            self.sgv = True
        else:
            self.sgv = False
        if 'spnv' in categories:
            self.spnv = True
        else:
            self.spnv = False
        if 'spfv' in categories:
            self.spfv = True
        else:
            self.spfv = False

        db.session.add(self)
        db.session.commit()

    @property
    def cost_effective_traction(self):
        cost_traction = self.cost_all_tractions
        try:
            traction = min(cost_traction, key=cost_traction.get)
        except ValueError:
            logging.warning(f"No Cost Calculation for master_area {self.id}")
            traction = 'no calculated cost'

        return traction

    @property
    def proportion_traction_optimised_electrification(self):
        proportion_traction_by_km = {
            'battery': 0,
            'electrification': 0
        }
        proportion_infrastructure_cost = {
            'battery': 0,
            'electrification': 0
        }

        for area in self.sub_master_areas:
            effective_traction = area.cost_effective_traction
            proportion_traction_by_km[effective_traction] += area.length/1000
            proportion_infrastructure_cost[effective_traction] += area.infrastructure_cost_all_tractions[effective_traction]

        proportion_traction = {
            "infrastructure_kilometer": proportion_traction_by_km,
            "infrastructure_cost": proportion_infrastructure_cost
        }

        return proportion_traction

    def calc_operating_cost(self, traction, infra_version, order_calculation_methods=None, traingroup_to_traction=None, overwrite=False):
        """
        get the train costs for all traingroups in that area.
        Checks first if cost calculation for area exists. If yes, this will be used.
        Otherwise, the train costs for that traction gets calculated
        :param traction:
        :param order_calculation_methods: sets the order in which the calculation methods are searched.
        :return:
        """
        if order_calculation_methods is None:
            order_calculation_methods = ["standi", "bvwp"]

        ttc_list = []
        for tg in self.traingroups:
            if traction == 'optimised_electrification':
                traction_optimised_electrification = TractionOptimisedElectrification.query.filter(
                    TractionOptimisedElectrification.master_area_id == self.id,
                    TractionOptimisedElectrification.traingroup_id == tg.id
                ).scalar()
                if traction_optimised_electrification is None:
                    raise NoTractionFound(
                        f"There is no caclculated traction for tg {tg} for masterarea {self.id}"
                    )
                else:
                    traction_train = traction_optimised_electrification.traction
            else:
                traction_train = traction

            for method in order_calculation_methods:
                ttc = TimetableTrainCost.query.filter(
                    TimetableTrainCost.traingroup_id == tg.id,
                    TimetableTrainCost.calculation_method == method,
                    TimetableTrainCost.master_scenario_id == self.scenario_id,
                    TimetableTrainCost.traction == traction_train
                ).scalar()

                if ttc:
                    ttc_list.append(ttc)
                    break

            if overwrite is True and ttc is not None:
                db.session.delete(ttc)
                db.session.commit()
                ttc = None

            if ttc is None:
                ttc = TimetableTrainCost.create(
                    traingroup=tg,
                    master_scenario_id=self.scenario_id,
                    traction=traction,
                    infra_version=infra_version
                )
                ttc_list.append(ttc)
            # except Exception as e:
            #     logging.error(f"Error at TimetableTrainCost calculation {e}")
            #     continue

        return ttc_list

    def calculate_infrastructure_cost(self, traction, infra_version, overwrite, battery_electrify_start_ocps=True, recalc_sub_areas=False):
        """
        Calculates the cost for the infrastructure
        :param battery_electrify_start_ocps:
        :param traction:
        :param infra_version:
        :param overwrite:
        :return:
        """
        name = f"{traction} s{self.scenario_id}-a{self.id}"

        """
        Check if infrastructure cost exists for the traction.
        If it exists and overwrite not active, it will return the project and returns
        otherwise the project will be deleted and the new calculation will begin.
        """
        try:
            pc = ProjectContent.query.filter(
            ProjectContent.master_areas.contains(self),
            ProjectContent.name.like(f'{traction}%')
            ).scalar()
        except sqlalchemy.exc.MultipleResultsFound:  # if that happens, there is a residual of an old error in the db -> cleans it up and continues
            pcs = ProjectContent.query.filter(
                ProjectContent.master_areas.contains(self),
                ProjectContent.name.like(f'{traction}%')
            ).all()
            for pc_delete in pcs:
                pc_delete.master_areas = []
                db.session.delete(pc_delete)
            pc = None

        if pc and overwrite is False:
            return pc
        elif pc and overwrite is True:
            db.session.delete(pc)
            db.session.commit()  # and calculate a new project_content

        if traction == 'optimised_electrification' and (overwrite is True or pc is None):
            for sub_area in self.sub_master_areas:
                for sub_pc in sub_area.project_contents:
                    sub_pc.master_areas = []
                    db.session.delete(sub_pc)

        """
        if the traction is optimised electrification -> check if sub areas are created and if not, recreate thenm
        """
        if recalc_sub_areas is True and traction == 'optimised_electrification':
            for sub_area in self.sub_master_areas:
                db.session.delete(sub_area)
            self.create_sub_areas()

        if traction == 'optimised_electrification' and len(self.sub_master_areas) == 0:
            self.create_sub_areas()

        """
        Calculate the infrastructure cost
        """
        from prosd.calculation_methods.cost import BvwpCostElectrification, BvwpProjectBattery, BvwpProjectOptimisedElectrification, BvwpFillingStation
        start_year_planning = parameter.START_YEAR - (parameter.DURATION_PLANNING + parameter.DURATION_BUILDING)

        pc_data = dict()
        if traction == "electrification":
            infrastructure_cost = BvwpCostElectrification(
                start_year_planning=start_year_planning,
                railway_lines_scope=self.railway_lines,
                infra_version=infra_version
            )
            pc_data["elektrification"] = True
            pc_data["length"] = infrastructure_cost.length
            pc_data["railway_lines"] = self.railway_lines.copy()

        elif traction == "battery":
            infrastructure_cost = BvwpProjectBattery(
                start_year_planning=start_year_planning,
                area=self,
                infra_version=infra_version,
                battery_electrify_start_ocps=battery_electrify_start_ocps
            )
            pc_data["battery"] = True

        elif traction == "optimised_electrification":
            infrastructure_cost = BvwpProjectOptimisedElectrification(
                start_year_planning=start_year_planning,
                area=self,
                infra_version=infra_version
            )
            pc_data["optimised_electrification"] = True

        elif traction == 'efuel':
            infrastructure_cost = BvwpFillingStation(
                start_year_planning=start_year_planning,
                cost_filling_station=parameter.COST_STATION_EFUEL,
                infrastructure_type='filling station efuel',
                area=self,
                infra_version=infra_version,
                kilometer_per_station=parameter.KILOMETER_PER_STATION_EFUEL
            )
            pc_data["filling_stations_efuel"] = True
            pc_data["filling_stations_count"] = infrastructure_cost.count_stations

        elif traction == 'diesel':
            infrastructure_cost = BvwpFillingStation(
                start_year_planning=start_year_planning,
                cost_filling_station=parameter.COST_STATION_DIESEL,
                infrastructure_type='filling station diesel',
                area=self,
                infra_version=infra_version,
                kilometer_per_station=parameter.KILOMETER_PER_STATION_DIESEL
            )
            pc_data["filling_stations_diesel"] = True
            pc_data["filling_stations_count"] = infrastructure_cost.count_stations

        elif traction == 'h2':
            infrastructure_cost = BvwpFillingStation(
                start_year_planning=start_year_planning,
                cost_filling_station=parameter.COST_STATION_H2,
                infrastructure_type='filling station h2',
                area=self,
                infra_version=infra_version,
                kilometer_per_station=parameter.KILOMETER_PER_STATION_H2
            )
            pc_data["filling_stations_h2"] = True
            pc_data["filling_stations_count"] = infrastructure_cost.count_stations

        else:
            logging.error(f"no fitting traction found for {traction}")
            return None

        """
        Create a project_content with the calculated costs
        """
        if hasattr(infrastructure_cost, "project_contents"):
            pc_data["sub_project_contents"] = []
            for subproject in infrastructure_cost.project_contents:
                subproject_prepared = infra_version.prepare_commit_project_content(subproject)
                pc_data["sub_project_contents"].append(subproject_prepared)

        pc_data["name"] = name
        pc_data["master_areas"] = [self]

        if 'spfv' in self.categories:
            pc_data["effects_passenger_long_rail"] = True
        else:
            pc_data["effects_passenger_long_rail"] = False

        if 'spnv' in self.categories:
            pc_data["effects_passenger_local_rail"] = True
        else:
            pc_data["effects_passenger_local_rail"] = False

        if 'sgv' in self.categories:
            pc_data["effects_cargo_rail"] = True
        else:
            pc_data["effects_cargo_rail"] = False

        pc_data["planned_total_cost"] = infrastructure_cost.cost_2015
        pc_data["maintenance_cost"] = infrastructure_cost.maintenance_cost_2015
        pc_data["planning_cost"] = infrastructure_cost.planning_cost_2015
        pc_data["investment_cost"] = infrastructure_cost.investment_cost_2015
        pc_data["capital_service_cost"] = infrastructure_cost.capital_service_cost_2015

        pc = ProjectContent(**pc_data)

        db.session.add(pc)
        db.session.commit()

        if traction == "optimised_electrification":
            traction_traingroups = []
            for tg, traction in infrastructure_cost.traingroup_to_traction.items():
                traction_traingroup = TractionOptimisedElectrification.query.filter(
                    TractionOptimisedElectrification.traingroup_id == tg.id,
                    TractionOptimisedElectrification.master_area_id == self.id
                ).scalar()
                if traction_traingroup is None:
                    traction_traingroup = TractionOptimisedElectrification(
                        traingroup_id = tg.id,
                        master_area_id=self.id,
                        traction=traction
                    )
                else:
                    traction_traingroup.traction = traction
                traction_traingroups.append(traction_traingroup)

            db.session.add_all(traction_traingroups)
            db.session.commit()

        return pc

    def calculate_cost(self, infra_version, overwrite_infrastructure, overwrite_operating_cost=False):
        """
        calculate infrastructure and operating cost for one area
        :return:
        """
        tractions = parameter.TRACTIONS
        for traction in tractions:
            if 'sgv' in self.categories and (traction == 'battery' or traction == 'h2'):
                continue
            else:
                start_time = time.time()
                self.calculate_infrastructure_cost(traction=traction, infra_version=infra_version, overwrite=overwrite_infrastructure)
                self.calc_operating_cost(traction=traction, infra_version=infra_version, overwrite=overwrite_operating_cost)
                end_time = time.time()
                logging.info(f"finished calculation {traction} {self.id} (duration {end_time - start_time}s)")

    def create_sub_areas(self):
        """
        clusters the infrastructure of one area in sub_areas, that have exactly the same traingroups
        :param infra_version:
        :return:
        """
        area_lines = self.railway_lines.copy()
        sub_areas = list()

        while area_lines:
            line = area_lines[0]
            lines_same_traingroups = get_lines_with_same_traingroups(line=line, scenario_id=self.scenario_id, area_lines=area_lines)
            area = MasterArea(
                scenario_id=self.scenario_id,
                superior_master_id=self.id,
                traingroups=line.get_traingroup_for_scenario(self.scenario_id),
                railway_lines=lines_same_traingroups
            )
            sub_areas.append(area)
            # remove the now used railway_lines from the while loop
            area_lines = [line for line in area_lines if line not in lines_same_traingroups]

        db.session.add_all(sub_areas)
        db.session.commit()

    def delete_sub_areas(self):
        """
        deletes the areas that are sub_areas for that area
        :return:
        """
        areas = MasterArea.query.filter(MasterArea.superior_master_id == self.id).all()
        pc_delete = []
        for area in areas:
            area.traingroups = []
            area.railway_lines = []
            pc_delete.extend(area.project_contents)
            area.project_contents = []

        for pc in pc_delete:
            db.session.delete(pc)

        for area in areas:
            db.session.delete(area)

        db.session.commit()


class TractionOptimisedElectrification(db.Model):
    __tablename__ = 'traction_optimised_electrification'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    traingroup_id = db.Column(db.String(255), db.ForeignKey('timetable_train_groups.id'), nullable=False)
    master_area_id = db.Column(db.Integer, db.ForeignKey('master_areas.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    traction = db.Column(db.String(50), nullable=False)

    traingroup = db.relationship("TimetableTrainGroup", backref=db.backref('traction_optimised_electrification'))


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
            password, int(app.config.get('BCRYPT_LOG_ROUNDS'))
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


class BksAction(db.Model):
    __tablename__ = 'bks_action'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))
    report_text = db.Column(db.Text)
    report_process = db.Column(db.Text)
    review_1_start = db.Column(db.Text)
    review_1_done = db.Column(db.Text)
    review_1_next = db.Column(db.Text)
    review_1_status = db.Column(db.String(255))
    review_1_changed_aim = db.Column(db.Boolean)

    cluster_number = db.Column(db.String(255), db.ForeignKey('bks_cluster.number', onupdate='CASCADE', ondelete='SET NULL'), nullable=True)
    cluster = db.relationship("BksCluster", backref=db.backref('bks_action'))


class BksHandlungsfeld(db.Model):
    __tablename__ = 'bks_handlungsfeld'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255))
    text = db.Column(db.Text)


class BksCluster(db.Model):
    __tablename__ = 'bks_cluster'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255))
    starting_situation = db.Column(db.Text)
    proposed_solution = db.Column(db.Text)
    impact_assessment = db.Column(db.Text)
    handlungsfeld_id = db.Column(db.Integer, db.ForeignKey('bks_handlungsfeld.number', onupdate='CASCADE', ondelete='SET NULL'), nullable=True)
    handlungsfeld = db.relationship("BksHandlungsfeld", backref=db.backref('cluster'))

