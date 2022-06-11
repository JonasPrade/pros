import geoalchemy2.shape
import geojson
import json
import shapely

from prosd import db
from prosd import ma
from prosd import models

from marshmallow_sqlalchemy import ModelConverter, auto_field
from marshmallow import fields
from geoalchemy2.types import Geometry


# Model Converter for Geoalchemy
class GeoConverter(ModelConverter):
    SQLA_TYPE_MAPPING = {
        **ModelConverter.SQLA_TYPE_MAPPING,
        **{Geometry: fields.Str}
    }


# Defining the schemas
class ProjectGroupSchema(ma.SQLAlchemyAutoSchema):
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


class RailwayPointsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.RailwayPoint
        model_converter = GeoConverter
        include_fk = True


class ProjectContentSchema(ma.SQLAlchemyAutoSchema):
    budgets = ma.Nested(BudgetSchema, many=True)
    texts = ma.Nested(TextSchema, many=True)
    projectcontent_groups = ma.Nested(ProjectGroupSchema, many=True)
    projectcontent_railway_lines = ma.Nested(RailwayLinesSchema, many=True)

    class Meta:
        model = models.ProjectContent
        include_fk = True


class ProjectSchema(ma.SQLAlchemyAutoSchema):
    project_contents = ma.Nested(ProjectContentSchema, many=True)
    superior_project = ma.Nested(lambda: ProjectSchema)

    first_project_content = fields.Str()

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


    # TODO: Add a bounds field which searches the bounds of all geo combinded
    '''
    bounds_of_geo = fields.Method('bounds_geo')

    def bounds_geo(self, obj):
        return 'bounds'
    '''

