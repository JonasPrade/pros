from prosd import db
from geoalchemy2 import Geometry
from prosd import conf

# TODO: Table railway_line to projects

# allowed_values_type_of_station = conf.allowed_values_type_of_station  # TODO: Add enum to type of station

### m:n tables

# project to group
project_to_group = db.Table('project_to_group',
                            db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
                            db.Column('projectgroup_id', db.Integer, db.ForeignKey('project_groups.id'))
                            )

# project to railway Lines
project_to_line = db.Table('projects_to_lines',
                           db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
                           db.Column('railway_lines_id', db.Integer, db.ForeignKey('railway_lines.id'))
                           )

# project to railway points
project_to_railway_points = db.Table('projects_to_points',
                                     db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
                                     db.Column('railway_point_id', db.Integer, db.ForeignKey('railway_points.id')),
                                     )

texts_to_project_content = db.Table('texts_to_projects',
                                    db.Column('project_content_id', db.Integer, db.ForeignKey('projects_contents.id')),
                                    db.Column('text.id', db.Integer, db.ForeignKey('texts.id'))
                                    )


############ classes/Tables

class RailwayLine(db.Model):
    """
    defines a RailwayLine, which is part of a railway network and has geolocated attributes (Multiline oder Line)
    """
    # TODO: Check if this RailwayLine can be used for import RailML infrastructure
    __tablename__ = 'railway_lines'
    id = db.Column(db.Integer, primary_key=True)
    mifcode = db.Column(db.String(30))
    streckennummer = db.Column(db.Integer)
    direction = db.Column(db.Integer)
    length = db.Column(db.Integer)
    from_km = db.Column(db.Integer)
    to_km = db.Column(db.Integer)
    electrified = db.Column(db.String(20))
    number_tracks = db.Column(db.Integer)
    vmax = db.Column(db.String(20))
    type_of_transport = db.Column(db.String(20))
    #coordinates = db.Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=False)
    coordinates = db.Column(Geometry(srid=4326), nullable=False)

class RailwayPoint(db.Model):
    __tablename__ = 'railway_points'
    id = db.Column(db.Integer, primary_key=True)
    mifcode = db.Column(db.Integer)
    bezeichnung = db.Column(db.String(255))
    type = db.Column(db.String(255))  # db.Enum(allowed_values_type_of_station)
    db_kuerzel = db.Column(
        db.String(5))  # TODO: Connect that to DB Station Names, have in mind that we also have some Non-DB-stations

    ## References
    # projects_start = db.relationship('Project', backref='project_starts', lazy=True)
    # projects_end = db.relationship('Project', backref='project_ends', lazy=True)


class Project(db.Model):
    """
    defines a Project which can be related with (different) project contents and is connected m:n to RailwayLine
    """
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    ProjectGroup = db.Column(db.Integer, db.ForeignKey('project_groups.id'))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    # id_point_start_id = db.Column(db.Integer, db.ForeignKey('railway_points.id'))
    # id_point_end_id = db.Column(db.Integer, db.ForeignKey('railway_points.id'))
    superior_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))

    # references
    project_contents = db.relationship('ProjectContent', backref='project_contents', lazy=True)
    project_groups = db.relationship('ProjectGroup', secondary=project_to_group,
                                     backref=db.backref('project_groups', lazy=True))


class ProjectContent(db.Model):
    __tablename__ = 'projects_contents'
    # Basic informations
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    project_number = db.Column(db.String(50))  # string because bvwp uses strings vor numbering projects, don't ask
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # traffic forecast and economical data
    nkv = db.Column(db.Integer)
    length = db.Column(db.Integer)
    priority = db.Column(db.String(100))

    # properties of project
    nbs = db.Column(db.Boolean, nullable=False, default=False)
    elektrification = db.Column(db.Boolean, nullable=False, default=False)
    second_track = db.Column(db.Boolean, nullable=False, default=False)
    third_track = db.Column(db.Boolean, nullable=False, default=False)
    fourth_track = db.Column(db.Boolean, nullable=False, default=False)
    curve = db.Column(db.Boolean, nullable=False, default=False)
    platform = db.Column(db.Boolean, nullable=False, default=False)
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

    # environmental data
    # TODO: Add environmental data

    # financial data
    lfd_nr = db.Column(db.Integer)
    finve_nr = db.Column(db.Integer)
    bedarfsplan_nr = db.Column(db.Integer)
    planned_total_cost = db.Column(db.Integer)
    actual_cost = db.Column(db.Integer)


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
    type = db.Column(db.String(100))  # TODO: ENUM
