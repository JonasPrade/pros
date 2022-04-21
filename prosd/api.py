from flask import jsonify, request, Response

from prosd import app
from prosd import models
from prosd import views


@app.route("/project/<id>", methods=['GET'])
def project_get(id):
    project = models.Project.query.get(id)
    project_schema = views.ProjectSchema()
    output = project_schema.dump(project)
    return jsonify({'project': output})


@app.route("/project/<id>", methods=['POST'])
def project_create():
    data = request.get_json()
    project_schema = views.ProjectSchema()
    project = project_schema.load(data)

    status_code = Response(status=201)
    return status_code



@app.route("/projects")
def projects():
    projects = models.Project.query.all()
    projects_schema = views.ProjectSchema(many=True)
    output = projects_schema.dump(projects)
    return jsonify({'projects': output})

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


