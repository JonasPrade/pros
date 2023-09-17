#import geoalchemy2.shape
import geojson
import shapely
import json

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


class GeoJSONField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return json.loads(value)


class WKBField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        # Convert WKB to Shapely object
        geometry = geoalchemy2.shape.to_shape(value)

        if geometry.is_empty:
            return None

        # Convert Shapely object to GeoJSON-compatible format
        geojson_data = shapely.geometry.mapping(geometry)
        return geojson_data


# Defining the schemas
class ProjectGroupSchema(ma.SQLAlchemyAutoSchema):
    projects_content = ma.Nested(lambda: ProjectContentShortSchema, many=True, exclude=("projectcontent_groups",))
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
    projectcontent_groups = ma.Nested(ProjectGroupSchemaShort, many=True)
    sub_project_contents = ma.Nested(lambda: ProjectContentShortSchema(), many=True)
    superior_project_content = ma.Nested(lambda: ProjectContentShortSchema())

    class Meta:
        model = models.ProjectContent
        model_converter = GeoConverter

    geojson_representation = GeoJSONField()
    centroid = WKBField()


class ProjectContentShortSchema(ma.SQLAlchemySchema):
    projectcontent_groups = ma.Nested(ProjectGroupSchemaShort, many=True)

    class Meta:
        model = models.ProjectContent
        model_converter = GeoConverter
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
    battery = auto_field()
    h2 = auto_field()
    efuel = auto_field()
    filling_stations_efuel = auto_field()
    filling_stations_h2 = auto_field()
    filling_stations_diesel = auto_field()
    filling_stations_count = auto_field()
    closure = auto_field()
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
    sgv740m = auto_field()
    railroad_crossing = auto_field()
    new_estw = auto_field()
    new_dstw = auto_field()
    noise_barrier = auto_field()
    sanierung = auto_field()
    lp_12 = auto_field()
    lp_34 = auto_field()
    bau = auto_field()
    ibn_erfolgt = auto_field()
    superior_project_content_id = auto_field()
    geojson_representation = GeoJSONField()
    centroid = WKBField()


class ProjectSchema(ma.SQLAlchemyAutoSchema):
    project_contents = ma.Nested(ProjectContentSchema, many=True)
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

    vehicles_ids_composition = fields.Dict()


class RailMlOcpSchema(ma.SQLAlchemyAutoSchema):
    station = ma.Nested(RailwayStationSchema)

    class Meta:
        model = models.RailMlOcp
        include_fk = True


class TimetableTimeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TimetableTime
        include_fk = True

    arrival_with_day = fields.DateTime()
    departure_with_day = fields.DateTime()


class TimetableOcpSchemaShort(ma.SQLAlchemyAutoSchema):
    ocp = ma.Nested(RailMlOcpSchema)
    # times = ma.Nested(TimetableTimeSchema, many=True)

    class Meta:
        model = models.TimetableOcp
        include_fk = True


class TimetableOcpSchema(ma.SQLAlchemyAutoSchema):
    ocp = ma.Nested(RailMlOcpSchema)
    times = ma.Nested(TimetableTimeSchema, many=True)

    class Meta:
        model = models.TimetableOcp


class TimetableTrainPartSchemaShort(ma.SQLAlchemyAutoSchema):
    formation = ma.Nested(FormationSchema)
    timetable_ocps = ma.Nested(TimetableOcpSchemaShort, many=True)

    class Meta:
        model = models.TimetableTrainPart
        include_fk = True


class TimetableTrainPartSchema(ma.SQLAlchemyAutoSchema):
    formation = ma.Nested(FormationSchema)
    timetable_ocps = ma.Nested(TimetableOcpSchema, many=True)
    class Meta:
        model = models.TimetableTrainPart
        include_fk = True


class TimetableTrainSchema(ma.SQLAlchemyAutoSchema):
    train_part = ma.Nested(TimetableTrainPartSchemaShort)

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


class TimetableTrainGroupSchema(ma.SQLAlchemyAutoSchema):
    railway_lines = ma.Nested(RouteTraingroupSchema, many=True)
    trains = ma.Nested(TimetableTrainSchema, many=True)
    train_costs = ma.Nested(TimetableTrainCostSchema, many=True)

    class Meta:
        model = models.TimetableTrainGroup
        include_fk = True

    coords = fields.Method('create_one_geojson')

    def create_one_geojson(self, obj):
        coord_list = list()
        for route_traingroup in obj.railway_lines:
            line = route_traingroup.railway_line
            coord = shapely.wkb.loads(line.coordinates.desc, hex=True)
            coord_list.append(shapely.geometry.mapping(coord)["coordinates"])

        coord_multistring = geojson.MultiLineString(coord_list)

        return coord_multistring


class TimetableTrainGroupShortSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TimetableTrainGroup
        include_fk = True


class MasterAreaSchema(ma.SQLAlchemyAutoSchema):
    railway_lines = ma.Nested(RailwayLinesSchema, many=True)
    project_contents = ma.Nested(ProjectContentSchema, many=True)
    traingroups = ma.Nested(TimetableTrainGroupShortSchema, many=True)
    scenario = ma.Nested(lambda: MasterScenarioSchemaShort())
    sub_master_areas = ma.Nested(lambda: MasterAreaShortSchema(), many=True)

    class Meta:
        model = models.MasterArea
        include_fk = True

    cost_overview = fields.Dict()
    categories = fields.List(fields.Str())

    coords = fields.Method('create_one_geojson')

    def create_one_geojson(self, obj):
        coord_list = list()
        for line in obj.railway_lines:
            coord = shapely.wkb.loads(line.coordinates.desc, hex=True)
            coord_list.append(shapely.geometry.mapping(coord)["coordinates"])

        coord_multistring = geojson.MultiLineString(coord_list)

        return coord_multistring


class MasterAreaShortSchema(ma.SQLAlchemyAutoSchema):
    railway_lines = ma.Nested(RailwayLinesSchema, many=True)

    class Meta:
        model = models.MasterArea
        include_fk = True

    length = fields.Float()

    coords = fields.Method('create_one_geojson')

    def create_one_geojson(self, obj):
        coord_list = list()
        for line in obj.railway_lines:
            coord = shapely.wkb.loads(line.coordinates.desc, hex=True)
            coord_list.append(shapely.geometry.mapping(coord)["coordinates"])

        coord_multistring = geojson.MultiLineString(coord_list)

        return coord_multistring


class MasterAreaRunningKmSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.MasterArea
        include_fk = True

    running_km_traingroups = fields.List(fields.Dict())


class MasterScenarioSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.MasterScenario
        include_fk = True


class MasterScenarioSchemaShort(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.MasterScenario
        include_fk = False


class MasterScenarioRunningKmShort(ma.SQLAlchemyAutoSchema):
    master_areas = ma.Nested(MasterAreaRunningKmSchema, many=True)
    class Meta:
        model = models.MasterScenario
        include_fk = False


class TractionOptimisedElectrificationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.TractionOptimisedElectrification
        include_fk = True
