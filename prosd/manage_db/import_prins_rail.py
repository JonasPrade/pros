from prins import BvwpRail
from prosd import models, db
import logging

# TODO: Get all bvwp-projects from db
# TODO: iterate through the db

logging.basicConfig(filename='../log/log_import_prins_rail.log', encoding='utf-8', level=logging.DEBUG)

ProjectContent = models.ProjectContent

#project_list = ProjectContent.query.all()
project_list = ['L02']

Pc_to_state = models.project_contents_to_states
States = models.States
states = States.query.all()
Counties = models.Counties
Constituencies = models.Constituencies


for project in project_list:

    project_number = project

    project_content_id = ProjectContent.query.filter(ProjectContent.project_number == project_number).one().id

    # create a dict for all values to be updated
    bvwp = BvwpRail(project_number)
    dict_projet_content, pc_states, pc_counties, pc_constituencies = bvwp.update_db(all_states=states, all_counties=Counties, all_constituencies=Constituencies)

    # transfer the Bvwp object to the db via an update of a model project_content
    db.session.query(ProjectContent).filter(ProjectContent.project_number == project_number).update(
        dict_projet_content,
        synchronize_session=False
    )
    db.session.commit()

    #  Add states, counties and constituencies
    pc = db.session.query(ProjectContent).filter(ProjectContent.project_number == project_number).one()
    # project_contents to states
    pc.states = pc_states

    # project_contents to counties
    pc.counties = pc_counties

    # project_contents to constituencies
    pc.constituencies = pc_constituencies
    db.session.commit()

    logging.info('finished import to db for project: ' + project_number)
