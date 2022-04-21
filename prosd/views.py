from prosd import db
from prosd import ma
from prosd import models

from marshmallow_sqlalchemy import ModelConverter
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


class ProjectContentSchema(ma.SQLAlchemyAutoSchema):
    budgets = ma.Nested(BudgetSchema, many=True)
    texts = ma.Nested(TextSchema, many=True)

    class Meta:
        model = models.ProjectContent
        include_fk = True


class RailwayLinesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.RailwayLine
        model_converter = GeoConverter
        include_fk = True


class RailwayPointsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.RailwayPoint
        model_converter = GeoConverter
        include_fk = True


class ProjectSchema(ma.SQLAlchemyAutoSchema):
    project_groups = ma.Nested(ProjectGroupSchema, many=True)
    project_contents = ma.Nested(ProjectContentSchema, many=True)
    project_railway_lines = ma.Nested(RailwayLinesSchema, many=True)
    superior_project = ma.Nested(lambda: ProjectSchema)

    class Meta:
        model = models.Project
        include_fk = True
