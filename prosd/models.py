import datetime
import jwt

from geoalchemy2 import Geometry

from prosd import db, app, bcrypt

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


# classes/Tables

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
    number_tracks = db.Column(db.String(100))
    vmax = db.Column(db.String(20))
    type_of_transport = db.Column(db.String(20))
    strecke_kuerzel = db.Column(db.String(100))
    bahnart = db.Column(db.String(100))
    # coordinates = db.Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=False)
    coordinates = db.Column(Geometry(geometry_type='LINESTRING', srid=4326), nullable=False)


class RailwayPoint(db.Model):
    __tablename__ = 'railway_points'
    id = db.Column(db.Integer, primary_key=True)
    mifcode = db.Column(db.Integer)
    bezeichnung = db.Column(db.String(255))
    type = db.Column(db.String(255))  # db.Enum(allowed_values_type_of_station)
    db_kuerzel = db.Column(
        db.String(5))  # TODO: Connect that to DB Station Names, have in mind that we also have some Non-DB-stations

    # References
    # projects_start = db.relationship('Project', backref='project_starts', lazy=True)
    # projects_end = db.relationship('Project', backref='project_ends', lazy=True)


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
    superior_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))

    # references
    project_contents = db.relationship('ProjectContent', backref='project_contents', lazy=True)
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
    description = db.Column(db.Text)
    reason_project = db.Column(db.Text)
    bvwp_alternatives = db.Column(db.Text)

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
    planned_total_cost = db.Column(db.Integer)
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
    budgets = db.relationship('Budget', backref='budgets', lazy=True)
    texts = db.relationship('Text', secondary=texts_to_project_content,
                            backref=db.backref('texts', lazy=True))
    projectcontent_groups = db.relationship('ProjectGroup', secondary=projectcontent_to_group,
                                            backref=db.backref('project_groups', lazy=True))
    projectcontent_railway_lines = db.relationship('RailwayLine', secondary=projectcontent_to_line,
                                                   backref=db.backref('railway_lines', lazy=True))
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
    polygon = db.Column(Geometry(geometry_type='POLYGON', srid=4326), nullable=True)


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
    polygon = db.Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey('states.id'))


class Constituencies(db.Model):
    """
    Constituencies
    """
    __tablename__= 'constituencies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    polygon = db.Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
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
