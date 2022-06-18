from flask import jsonify, request, Response, make_response
from functools import wraps
from flask_cors import cross_origin

from prosd import app
from prosd import models
from prosd.models import Project
from prosd import views
from prosd.auth import views as auth

allowed_ip = 'http://localhost:3000'

# TODO Change auth.views to remove this stupid blueprints


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


@app.route("/project/<id>", methods=['POST'])
@cross_origin()
@token_required
def project_create():
    data = request.get_json()
    project_schema = views.ProjectSchema()
    project = project_schema.load(data)

    status_code = Response(status=201)
    return status_code


@app.route("/projects")
def projects():
    projects = models.Project.query.filter(models.Project.superior_project_id==None).all()
    projects_schema = views.ProjectSchema(many=True)
    output = projects_schema.dump(projects)
    response = make_response({'projects': output})
    #response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Origin'] = '*'
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

