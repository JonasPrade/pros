from flask import jsonify, request, Response, make_response
from functools import wraps
from flask_cors import cross_origin

from prosd import app
from prosd import models
from prosd.models import Project
from prosd import views
from prosd.auth import views as auth

allowed_ip = 'http://localhost:3000'


# Have in mind that the user login and authorization process is in /auth/views.py

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                auth_token = auth_header.split(" ")[1]
            except IndexError:
                responseObject = {
                    'status': 'fail',
                    'message': 'Bearer token malformed.'
                }
                return make_response(jsonify(responseObject)), 401
        else:
            auth_token = ''
        if auth_token:
            resp = models.User.decode_auth_token(auth_token)
            if not isinstance(resp, str):
                user = models.User.query.filter_by(id=resp).first()
                return f(user, *args, **kwargs)
            responseObject = {
                'status': 'fail',
                'message': resp
            }
            return make_response(jsonify(responseObject)), 401
        else:
            responseObject = {
                'status': 'fail',
                'message': 'Provide a valid auth token.'
            }
            return make_response(jsonify(responseObject)), 401
    return decorated


@app.route("/project/<id>", methods=['GET'])
@cross_origin()
@token_required
def project_get(user, **kwargs):
    project_id = kwargs.pop('id')
    project = models.Project.query.get(project_id)
    project_schema = views.ProjectSchema()
    output = project_schema.dump(project)
    response = make_response({'project': output})
    return response


@app.route("/projectgroups", methods=['GET'])
@cross_origin()
# @token_required
def get_projectgroups(**kwargs):
    project_groups = models.ProjectGroup.query.all()
    project_group_schema = views.ProjectGroupSchema(many=True)
    output = project_group_schema.dump(project_groups)
    response = make_response({'projectgroups': output})
    return response


@app.route("/projectgroup/first", methods=['GET'])
@cross_origin()
# @token_required
def get_first_projectgroup(**kwargs):
    project_groups = models.ProjectGroup.query.first()
    project_group_schema = views.ProjectGroupSchema()
    output = project_group_schema.dump(project_groups)
    response = make_response({'projectgroup': output})
    return response


@app.route("/traingroup/<id>", methods=['GET'])
@cross_origin()
def get_traingroup(**kwargs):
    traingroup_id = kwargs.pop('id')
    traingroup = models.TimetableTrainGroup.query.get(traingroup_id)
    traingroup_schema = views.TrainGroupSchema()
    output = traingroup_schema.dump(traingroup)
    response = make_response({'traingroup': output})
    return response


@app.route("/station/<id>", methods=['GET'])
@cross_origin()
def get_station(**kwargs):
    station_id = kwargs.pop('id')
    station = models.RailwayStation.query.get(station_id)
    station_schema = views.RailwayStationSchema()
    output = station_schema.dump(station)
    response = make_response({'station': output})
    return response


@app.route("/railwaypoint/<id>", methods=['GET'])
@cross_origin()
def get_railway_point(**kwargs):
    rw_point_id = kwargs.pop('id')
    rw_point = models.RailwayPoint.query.get(rw_point_id)
    point_schema = views.RailwayPointsSchema()
    output = point_schema.dump(rw_point)
    response = make_response({'point': output})
    return response


@app.route("/masterarea/<id>", methods=['GET'])
@cross_origin()
def get_master_areas(**kwargs):
    master_area_id = kwargs.pop('id')
    master_area = models.MasterArea.query.get(master_area_id)
    area_schema = views.MasterAreaSchema()
    output = area_schema.dump(master_area)
    response = make_response({'master_area': output})
    return response


@app.route("/masterarea_short/<id>", methods=['GET'])
@cross_origin()
def get_master_area_short(**kwargs):
    master_area_id = kwargs.pop('id')
    master_area = models.MasterArea.query.get(master_area_id)
    area_schema = views.MasterAreaShort()
    output = area_schema.dump(master_area)
    response = make_response({'master_area': output})
    return response


@app.route("/masterscenario/<id>", methods=['GET'])
@cross_origin()
def get_master_scenario(**kwargs):
    master_scenario_id = kwargs.pop('id')
    master_scenario = models.MasterScenario.query.get(master_scenario_id)
    scenario_schema = views.MasterScenarioSchema()
    output = scenario_schema.dump(master_scenario)
    response = make_response({'master_scenario': output})
    return response


@app.route("/main_masterareas_for_scenario/<id>", methods=['GET'])
@cross_origin()
def get_main_masterareas_for_scenario(**kwargs):
    master_scenario_id = kwargs.pop('id')
    master_areas = models.MasterArea.query.filter(
        models.MasterArea.scenario_id == master_scenario_id,
        models.MasterArea.superior_master_id == None
    )
    scenario_schema = views.MasterAreaShort(many=True)
    output = scenario_schema.dump(master_areas)
    response = make_response({'master_areas': output})
    return response


@app.route("/masterscenarios", methods=['GET'])
@cross_origin()
def get_all_master_scenarios(**kwargs):
    master_scenarios = models.MasterScenario.query.all()
    scenario_schema = views.MasterScenarioSchemaShort(many=True)
    output = scenario_schema.dump(master_scenarios)
    response = make_response({'master_scenario': output})
    return response

@app.route("/railwaylines", methods=['GET'])
@cross_origin()
def get_all_railwaylines(**kwargs):
    railway_lines = models.RailwayLine.query.all()
    railway_lines_schema = views.RailwayLinesSchema(many=True)
    output = railway_lines_schema.dump(railway_lines)
    response = make_response({'railway_lines': output})
    return response

"""
@app.route("/project/<id>", methods=['POST'])
@cross_origin()
@token_required
def project_create():
    data = request.get_json()
    project_schema = views.ProjectSchema()
    project = project_schema.load(data)

    status_code = Response(status=201)
    return status_code
"""

@app.route("/projects")
def projects_short():
    projects = models.Project.query.filter(models.Project.superior_project_content_id == None).all()
    projects_schema = views.ProjectShortSchema(many=True)
    output = projects_schema.dump(projects)
    response = make_response({'projects': output})
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route("/projects/group/<id>", methods=['GET'])
@cross_origin()
# @token_required
def get_projects_by_projectgroup(**kwargs):
    project_group_id = kwargs.pop('id')
    # get all projects that have a project_content that is part of the project_group_id
    project_group = models.ProjectGroup.query.get(project_group_id)
    projects = project_group.superior_projects
    project_schema = views.ProjectShortSchema(many=True)
    output = project_schema.dump(projects)
    response = make_response({"projects": output})
    return response


@app.route("/auth/login", methods=['POST'])
@cross_origin()
def auth_login():
    response = auth.login()
    # response[0].headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route("/auth/checktoken", methods=['POST'])
@cross_origin()
def check_token():
    response = auth.check_auth_token()
    return response


"""
@app.route("/projectgroups")
def projectgroups():
    projectgroups = models.ProjectGroup.query.all()
    project_groups_schema = views.ProjectGroupSchema(many=True)
    output = project_groups_schema.dump(projectgroups)
    return jsonify({'projectgroups': output})
"""

"""
@app.route("/projectcontent/<id>")
def projectcontent(id):
    projectcontent = models.ProjectContent.query.get(id)
    projectcontent_schema = views.ProjectContentSchema()
    output = projectcontent_schema.dump(projectcontent)
    return jsonify({'projectcontent': output})
"""

