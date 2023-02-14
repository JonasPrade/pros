#import geoalchemy2.shape
import geojson
import marshmallow
import shapely
import logging

from prosd import db
from prosd import ma
from prosd import models

from marshmallow_sqlalchemy import ModelConverter, auto_field, property2field
from marshmallow import fields
import geoalchemy2


# Model Converter for Geoalchemy
class GeoConverter(ModelConverter):
    SQLA_TYPE_MAPPING = {
        **ModelConverter.SQLA_TYPE_MAPPING,
        **{geoalchemy2.types.Geometry: fields.Str}
    }


# Defining the schemas
class ProjectGroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.ProjectGroup
        include_fk = True


class ProjectGroupSchemaShort(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.ProjectGroup
        include_fk = True


class TextTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TextType
        include_fk = True


class BudgetSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.Budget
        include_fk = True


class TextSchema(ma.SQLAlchemyAutoSchema):
    text_type = ma.Nested(TextTypeSchema(only=("name",)))

    class Meta:
        model = models.Text
        include_fk = True


class RailwayLinesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.RailwayLine
        # exclude = (['coordinates'])
        include_fk = True

    coordinates = fields.Method('geom_to_geojson')

    def geom_to_geojson(self, obj):
        coords = geoalchemy2.shape.to_shape(obj.coordinates)
        xy = coords.xy
        x_array = xy[0]
        y_array = xy[1]
        coords_geojson = []

        for x, y in zip(x_array, y_array):
            coords_geojson.append((x, y))

        geo = geojson.LineString(coords_geojson)
        return geo


class RailwayLinesShortSchema(ma.SQLAlchemySchema):
    class Meta:
        model = models.RailwayLine
        include_fk = True

    id = auto_field()
    coordinates = fields.Method('geom_to_geojson')

    def geom_to_geojson(self, obj):
        # TODO: No dopple use of this function
        coords = geoalchemy2.shape.to_shape(obj.coordinates)
        xy = coords.xy
        x_array = xy[0]
        y_array = xy[1]
        coords_geojson = []

        for x, y in zip(x_array, y_array):
            coords_geojson.append((x, y))

        geo = geojson.LineString(coords_geojson)
        return geo


class RailwayPointsSchema(ma.SQLAlchemyAutoSchema):
    station = ma.Nested("RailwayStationSchema")

    class Meta:
        model = models.RailwayPoint
        model_converter = GeoConverter
        include_fk = True

    coordinates = fields.Method('geom_to_geojson')

    def geom_to_geojson(self, obj):
        # TODO: No dopple use of this function
        coords = geoalchemy2.shape.to_shape(obj.coordinates)
        xy = coords.xy
        x_array = xy[0]
        y_array = xy[1]
        coords_geojson = []

        for x, y in zip(x_array, y_array):
            coords_geojson.append((x, y))

        geo = geojson.Point(coords_geojson)
        return geo


class RailwayStationSchema(ma.SQLAlchemyAutoSchema):
    railway_points = ma.Nested(lambda: RailwayPointsSchema(exclude=["station",]), many=True)

    class Meta:
        model = models.RailwayStation
        include_fk = True


class ProjectContentSchema(ma.SQLAlchemyAutoSchema):
    budgets = ma.Nested(BudgetSchema, many=True)
    texts = ma.Nested(TextSchema, many=True)
    projectcontent_groups = ma.Nested(ProjectGroupSchema, many=True)
    projectcontent_railway_lines = ma.Nested(RailwayLinesSchema, many=True)

    class Meta:
        model = models.ProjectContent

    coords = fields.Method('create_one_geojson')
    coords_centroid = fields.Method('get_centroid')

    def create_one_geojson(self, obj):
        coord_list = list()
        for line in obj.railway_lines:
            coord = shapely.wkb.loads(line.coordinates.desc, hex=True)
            coord_list.append(shapely.geometry.mapping(coord)["coordinates"])

        coord_multistring = geojson.MultiLineString(coord_list)

        return coord_multistring

    def get_centroid(self, obj):
        try:
            coord_list = list()
            for line in obj.railway_lines:
                coord = shapely.wkb.loads(line.coordinates.desc, hex=True)
                coord_list.append(shapely.geometry.mapping(coord)["coordinates"])

            coord_multistring = geojson.MultiLineString(coord_list)
            coord_multstring_wkt = shapely.geometry.shape(coord_multistring)  # TODO: Opose that multiestring also, so als geojson as on (no iteration in browser needed)
            centroid = coord_multstring_wkt.centroid
            centroid = shapely.geometry.mapping(centroid)
            return centroid
        except IndexError:
            logging.warning("Error while calculating centroid. Possibly no geo coordinates?")


class ProjectContentShortSchema(ma.SQLAlchemySchema):
    projectcontent_groups = ma.Nested(ProjectGroupSchema, many=True)
    projectcontent_railway_lines = ma.Nested(RailwayLinesShortSchema, many=True)
    class Meta:
        model = models.ProjectContent
        include_fk = True

    id = auto_field()
    project_number = auto_field()
    name = auto_field()
    description = auto_field()
    nkv = auto_field()
    length = auto_field()
    priority = auto_field()
    nbs = auto_field()
    abs = auto_field()
    charging_station = auto_field()
    etcs = auto_field()
    etcs_level = auto_field()
    elektrification = auto_field()
    second_track = auto_field()
    third_track = auto_field()
    fourth_track = auto_field()
    curve = auto_field()
    platform = auto_field()
    junction_station = auto_field()
    number_junction_station = auto_field()
    overtaking_station = auto_field()
    number_overtaking_station = auto_field()
    double_occupancy = auto_field()
    block_increase = auto_field()
    flying_junction = auto_field()
    tunnel_structural_gauge = auto_field()
    increase_speed = auto_field()
    new_vmax = auto_field()
    level_free_platform_entrance = auto_field()
    etcs = auto_field()
    etcs_level = auto_field()
    planned_total_cost = auto_field()
    actual_cost = auto_field()
    bvwp_planned_cost = auto_field()
    ibn_planned = auto_field()
    ibn_final = auto_field()
    hoai = auto_field()
    parl_befassung_planned = auto_field()
    parl_befassung_date = auto_field()
    ro_finished = auto_field()
    ro_finished_date = auto_field()
    pf_finished = auto_field()
    pf_finished_date = auto_field()
    bottleneck_elimination = auto_field()
    traveltime_reduction = auto_field()
    delta_co2 = auto_field()
    effects_passenger_long_rail = auto_field()
    effects_passenger_local_rail = auto_field()
    effects_cargo_rail = auto_field()


class ProjectSchema(ma.SQLAlchemyAutoSchema):
    project_contents = ma.Nested(ProjectContentSchema, many=True)
    # superior_project = ma.Nested(lambda: ProjectSchema)

    class Meta:
        model = models.Project
        include_fk = True

    first_project_content = fields.Method('get_first_project_content')

    def get_first_project_content(self, obj):
        # TODO: function is doubled
        if obj.project_contents:
            first_project_content = obj.project_contents[0].id
        else:
            first_project_content = None

        # first_project_content = obj.project_contents[0]
        return first_project_content

    # TODO: Add a bounds field which searches the bounds of all geo combinded
    '''
    bounds_of_geo = fields.Method('bounds_geo')

    def bounds_geo(self, obj):
        return 'bounds'
    '''


class ProjectShortSchema(ma.SQLAlchemyAutoSchema):
    project_contents = ma.Nested(ProjectContentShortSchema, many=True)
    # superior_project = ma.Nested(lambda: ProjectSchema)

    class Meta:
        model = models.Project
        include_fk = True

    first_project_content = fields.Method('get_first_project_content')

    def get_first_project_content(self, obj):
        if obj.project_contents:
            first_project_content = obj.project_contents[0].id
        else:
            first_project_content = None

        # first_project_content = obj.project_contents[0]
        return first_project_content


class VehicleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.Vehicle
        include_fk = True


class FormationSchema(ma.SQLAlchemyAutoSchema):
    vehicles = ma.Nested(VehicleSchema, many=True)

    class Meta:
        model = models.Formation
        include_fk = True


class RailMlOcpSchema(ma.SQLAlchemyAutoSchema):
    station = ma.Nested(RailwayStationSchema)

    class Meta:
        model = models.RailMlOcp
        include_fk = True


class TimetableTimeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TimetableTime
        include_fk = True


class TimetableOcpSchema(ma.SQLAlchemyAutoSchema):
    ocp = ma.Nested(RailMlOcpSchema)
    # times = ma.Nested(TimetableTimeSchema, many=True)

    class Meta:
        model = models.TimetableOcp
        include_fk = True


class TimetableTrainPartSchema(ma.SQLAlchemyAutoSchema):
    formation = ma.Nested(FormationSchema)
    timetable_ocps = ma.Nested(TimetableOcpSchema, many=True)

    class Meta:
        model = models.TimetableTrainPart
        include_fk = True


class TimetableTrainSchema(ma.SQLAlchemyAutoSchema):
    train_part = ma.Nested(TimetableTrainPartSchema)

    class Meta:
        model = models.TimetableTrain
        include_fk = True


class RouteTraingroupSchema(ma.SQLAlchemyAutoSchema):
    railway_line = ma.Nested(RailwayLinesSchema)

    class Meta:
        model = models.RouteTraingroup
        include_fk = True


class TimetableTrainCostSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TimetableTrainCost
        include_fk = True


class TrainGroupSchema(ma.SQLAlchemyAutoSchema):
    railway_lines = ma.Nested(RouteTraingroupSchema, many=True)
    trains = ma.Nested(TimetableTrainSchema, many=True)
    train_costs = ma.Nested(TimetableTrainCostSchema, many=True)

    class Meta:
        model = models.TimetableTrainGroup
        include_fk = True


class TrainGroupShortSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TimetableTrainGroup
        include_fk = True


class MasterAreaSchema(ma.SQLAlchemyAutoSchema):
    railway_lines = ma.Nested(RailwayLinesSchema, many=True)
    project_contents = ma.Nested(ProjectContentShortSchema, many=True)
    traingroups = ma.Nested(TrainGroupShortSchema, many=True)
    scenario = ma.Nested(lambda: MasterScenarioSchema(exclude=["master_areas",]))

    class Meta:
        model = models.MasterArea
        include_fk = True

    cost_all_tractions = fields.Dict()
    infrastructure_cost_all_tractions = fields.Dict()
    operating_cost_all_tractions = fields.Dict()
    cost_effective_traction = fields.Str()
    categories = fields.List(fields.Str())


class MasterScenarioSchema(ma.SQLAlchemyAutoSchema):
    master_areas = ma.Nested(MasterAreaSchema(exclude=["scenario",]), many=True)

    class Meta:
        model = models.MasterScenario
        include_fk = True


class MasterScenarioSchemaShort(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.MasterScenario
        include_fk = False
