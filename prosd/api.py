from flask import jsonify, request, make_response
from functools import wraps
from flask_cors import cross_origin
import sqlalchemy

from prosd import app, db
from prosd import models
from prosd import views
from prosd.auth import views as auth

# user login and authorization process is in /auth/views.py


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
def project_get(**kwargs):
    project_id = kwargs.pop('id')
    project = models.Project.query.get(project_id)
    project_schema = views.ProjectSchema()
    output = project_schema.dump(project)
    response = make_response({'project': output})
    return response


@app.route("/projectgroups", methods=['GET'])
@cross_origin()
# @token_required
def get_projectgroups():
    project_groups = models.ProjectGroup.query.filter(models.ProjectGroup.public == True).order_by(models.ProjectGroup.id).all()
    project_group_schema = views.ProjectGroupSchemaShort(many=True)
    output = project_group_schema.dump(project_groups)
    response = make_response({'projectgroups': output})
    return response


@app.route("/projectgroup/first", methods=['GET'])
@cross_origin()
# @token_required
def get_first_projectgroup():
    project_groups = models.ProjectGroup.query.first()
    project_group_schema = views.ProjectGroupSchemaShort()
    output = project_group_schema.dump(project_groups)
    response = make_response({'projectgroup': output})
    return response


@app.route("/projectgroupsbyid", methods=['GET'])
@cross_origin()
def getprojectgroupsbyid():
    projectgroups_id = request.args.getlist('id')
    projectgroups_id = [int(x) for x in projectgroups_id]
    projectgroups = models.ProjectGroup.query.filter(models.ProjectGroup.id.in_(projectgroups_id))
    projectgroups_schema = views.ProjectGroupSchema(many=True)
    output = projectgroups_schema.dump(projectgroups)
    response = make_response({'projectgroups': output})
    return response


@app.route("/traingroup/<id>", methods=['GET'])
@cross_origin()
def get_traingroup(**kwargs):
    traingroup_id = kwargs.pop('id')
    traingroup = models.TimetableTrainGroup.query.get(traingroup_id)
    traingroup_schema = views.TimetableTrainGroupSchema()
    output = traingroup_schema.dump(traingroup)
    response = make_response({'traingroup': output})
    return response


@app.route("/trainpart/<id>", methods=['GET'])
@cross_origin()
def get_trainpart(**kwargs):
    trainpart_id = kwargs.pop('id')
    trainpart = models.TimetableTrainPart.query.get(trainpart_id)
    trainpart_schema = views.TimetableTrainPartSchema()
    output = trainpart_schema.dump(trainpart)
    response = make_response({'trainpart': output})
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
    area_schema = views.MasterAreaShortSchema()
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
    scenario_schema = views.MasterAreaShortSchema(many=True)
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


@app.route("/masterarea_optimised_traingroups/<id>", methods=['GET'])
@cross_origin()
def masterarea_optimised_traingroups(**kwargs):
    master_area_id = kwargs.pop('id')
    tractions = models.TractionOptimisedElectrification.query.filter(models.TractionOptimisedElectrification.master_area_id == master_area_id)
    tractions_schema = views.TractionOptimisedElectrificationSchema(many=True)
    output = tractions_schema.dump(tractions)
    response = make_response({'tractions': output})
    return response


@app.route("/traingroups-scenario/<id>", methods=['GET'])
@cross_origin()
def running_km_for_scenario(**kwargs):
    master_scenario_id = kwargs.pop('id')
    master_scenario = models.MasterScenario.query.get(master_scenario_id)
    area_schema = views.MasterScenarioRunningKmShort()
    output = area_schema.dump(master_scenario)
    response = make_response({'master_scenario': output})
    return response


@app.route("/projectcontentsbygroup/<id>", methods=['GET'])
@cross_origin()
def get_projectscontent_by_projectgroup(**kwargs):
    project_group_id = kwargs.pop('id')
    # project_group = models.ProjectGroup.query.get(project_group_id)
    pcs = db.session.query(models.ProjectContent).join(models.ProjectContent.projectcontent_groups).filter(models.ProjectGroup.id == project_group_id).filter(models.ProjectContent.superior_project_content_id == None).all()
    pc_schema = views.ProjectContentShortSchema(many=True)
    output = pc_schema.dump(pcs)
    response = make_response({'pcs': output})
    return response


@app.route("/projectcontentshort/<id>", methods=['GET'])
@cross_origin()
def get_projectcontentshort(**kwargs):
    pc_id = kwargs.pop('id')
    project_content = models.ProjectContent.query.get(pc_id)
    pc_schema = views.ProjectContentShortSchema()
    output = pc_schema.dump(project_content)
    response = make_response({'pc': output})
    return response


@app.route("/projectcontent/<id>", methods=['GET'])
@cross_origin()
def get_projectcontent(**kwargs):
    pc_id = kwargs.pop('id')
    project_content = models.ProjectContent.query.get(pc_id)
    pc_schema = views.ProjectContentSchema()
    output = pc_schema.dump(project_content)
    response = make_response({'pc': output})
    return response


@app.route("/projects")
@cross_origin()
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


@app.route("/traingroupcostscenario/<masterscenario_id>/<traingroup_id>", methods=['GET'])
@cross_origin()
def train_cost_traingroup_scenario(**kwargs):
    master_scenario_id = kwargs.pop('masterscenario_id')
    traingroup_id = kwargs.pop('traingroup_id')
    train_cost = models.TimetableTrainCost.query.filter(
        models.TimetableTrainCost.master_scenario_id == master_scenario_id,
        models.TimetableTrainCost.traingroup_id == traingroup_id
    )
    train_cost_schema = views.TimetableTrainCostSchema(many=True)
    output = train_cost_schema.dump(train_cost)
    response = make_response({'train_cost': output})
    return response


@app.route("/textbypcandtexttype/<projectcontent_id>/<texttype_id>", methods=['GET'])
@cross_origin()
def textbypcandtexttype(**kwargs):
    projectcontent_id = kwargs.pop('projectcontent_id')
    texttype_id = kwargs.pop('texttype_id')
    texts = models.Text.query.join(models.TextType).join(models.texts_to_project_content).join(models.ProjectContent).filter(
        models.TextType.id == texttype_id,
        models.ProjectContent.id == projectcontent_id
    )
    text_schema = views.TextSchema(many=True)
    output = text_schema.dump(texts)
    response = make_response({'texts': output})
    return response


@app.route("/subprojects-progress/<int:projectcontent_id>", methods=['GET'])
@cross_origin()
def projectcontent_subprojects_progress(**kwargs):
    projectcontent_id = kwargs.pop('projectcontent_id')
    projectcontent = models.ProjectContent.query.get(projectcontent_id)
    progress = projectcontent.calc_progress_sub_projects()
    response = make_response({'progress': progress})
    return response


@app.route("/search/projectcontent/<string:search_string>", methods=['GET'])
@cross_origin()
def search_projectcontent_by_string(**kwargs):
    # searches for the search string in ProjectContent Model and returns a list of ProjectContent objects
    # can be limited to some ProjectGroups
    search_string = kwargs.pop('search_string')
    if search_string == 'null' or search_string == 'all':
        search_string = '%'  # search for all

    projectgroups_id = [int(x) for x in request.args.getlist('projectgroup_id')]
    projectcontents = db.session.query(models.ProjectContent).join(models.projectcontent_to_group).join(models.ProjectGroup).filter(
        sqlalchemy.or_(
            models.ProjectContent.name.like('%' + search_string + '%'),
            models.ProjectContent.description.like('%' + search_string + '%')
        ), models.ProjectGroup.id.in_(projectgroups_id)
    ).distinct(models.ProjectContent.id).order_by(
        models.ProjectContent.id
    ).all()
    output = views.ProjectContentShortSchema(many=True).dump(projectcontents)
    response = make_response({'projects': output})
    return response

@app.route("/search/finve/<string:search_string>", methods=['GET'])
@cross_origin()
def search_finve_by_string(**kwargs):
    # searches for the search string in Finve and returns all finve inclusive budget
    search_string = kwargs.pop('search_string')
    if search_string == 'null' or search_string == 'all':
        search_string = '%'
    finve = db.session.query(models.FinVe).filter(
        models.FinVe.name.like('%' + search_string + '%'),
    ).distinct(models.FinVe.id).all()
    output = views.FinveSchema(many=True).dump(finve)
    response = make_response({'finve': output})
    return response


@app.route("/subprojects-progress/<int:projectcontent_id>", methods=['GET'])
@cross_origin()
def search_projectcontent(**kwargs):
    projectcontent_id = kwargs.pop('projectcontent_id')
    projectcontent = models.ProjectContent.query.get(projectcontent_id)
    progress = projectcontent.calc_progress_sub_projects()
    response = make_response({'progress': progress})
    return response


@app.route("/bkshandlungsfeld-all", methods=['GET'])
@cross_origin()
def get_bks_handlungsfeld(**kwargs):
    bks_handlungsfelds = models.BksHandlungsfeld.query.all()
    bks_handlungsfeld_schema = views.BksHandlungsfeldSchema(many=True)
    output = bks_handlungsfeld_schema.dump(bks_handlungsfelds)
    response = make_response({'bks_handlungsfelder': output})
    return response


@app.route("/bksaction/<id>", methods=['GET'])
@cross_origin()
def get_bks_action(**kwargs):
    bks_action_id = kwargs.pop('id')
    bks_action = models.BksAction.query.get(bks_action_id)
    bks_action_schema = views.BksActionSchema()
    output = bks_action_schema.dump(bks_action)
    response = make_response({'action': output})
    return response


@app.route("/netzzustandsbericht/all", methods=['GET'])
@cross_origin()
def get_all_netzzustandsbericht(**kwargs):
    netzzustandsberichts = models.Netzzustandsbericht.query.all()
    netzzustandsbericht_schema = views.NetzzustandsberichtSchema(many=True)
    output = netzzustandsbericht_schema.dump(netzzustandsberichts)
    response = make_response({'netzzustandsberichte': output})
    return response


@app.route("/finve/<int:id>", methods=['GET'])
@cross_origin()
def get_finve(**kwargs):
    finve_id = kwargs.pop('id')
    finve = models.FinVe.query.get(finve_id)
    finve_schema = views.FinveMainSchema()
    output = finve_schema.dump(finve)
    response = make_response({'finve': output})
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

