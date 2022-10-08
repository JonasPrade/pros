import pandas
import math

from prosd import db
from prosd.models import ProjectContent, Project, ProjectGroup
import csv


def add_project_content(pd, project_group_id, update=False):
    project = Project(
        name=pd["project_name"],
        # superior_project_content_id=pd["superior_project_content_id"],
    )
    db.session.add(project)
    db.session.commit()
    db.session.refresh(project)

    project_group = ProjectGroup.query.get(project_group_id)

    if math.isnan(pd["number_junction_station"]):
        pd["number_junction_station"] = 0

    if math.isnan(pd["number_overtaking_station"]):
        pd["number_overtaking_station"] = 0

    if math.isnan(pd["new_vmax"]):
        pd["new_vmax"] = 0

    if math.isnan(pd["etcs_level"]):
        pd["etcs_level"] = None
    else:
        pd["etcs_level"] = float(pd["etcs_level"])

    pc = ProjectContent(
        project=project,
        projectcontent_groups=[project_group],
        project_number=pd["project_number"],
        name=pd["pc_name"],
        description=pd["pc_description"],
        reason_project=pd["pc_reason"],
        effects_passenger_long_rail=bool(pd["effect_long_rail"]),
        effects_passenger_local_rail=bool(pd["effect_local_rail"]),
        effects_cargo_rail=bool(pd["effect_cargo"]),
        nbs=bool(pd["nbs"]),
        abs=bool(pd["abs"]),
        elektrification=bool(pd["elektrification"]),
        batterie=bool(pd["batterie"]),
        second_track=bool(pd["second_track"]),
        third_track=bool(pd["third_track"]),
        fourth_track=bool(pd["fourth_track"]),
        curve=bool(pd["curve"]),
        platform=bool(pd["platform"]),
        junction_station=bool(pd["junction_station"]),
        number_junction_station=int(pd["number_junction_station"]),
        overtaking_station=bool(pd["overtaking_station"]),
        number_overtaking_station=int(pd["number_overtaking_station"]),
        double_occupancy=bool(pd["double_occupancy"]),
        block_increase=bool(pd["block_increase"]),
        flying_junction=bool(pd["flying_junction"]),
        tunnel_structural_gauge=bool(pd["tunnel_structural_gauge"]),
        increase_speed=bool(pd["increase_speed"]),
        new_vmax=float(pd["new_vmax"]),
        level_free_platform_entrance=bool(pd["level_free_platform_entrance"]),
        etcs=bool(pd["etcs"]),
        etcs_level=pd["etcs_level"],
        new_station=bool(pd["new_station"]),
        depot=bool(pd["depot"]),
        station_railroad_switches=bool(pd["station_railroad_switches"]),
        planned_total_cost=float(pd["planned_total_cost"])
    )
    db.session.add(pc)
    db.session.commit()

    # TODO: railway_lines
    # TODO: constituencies
    # TODO: counties
    # TODO: states


# # import project_content.csv als Datenquelle
# filename = '../../example_data/import/project_content.csv'
# with open(filename, mode='r') as inp:
#     reader = csv.reader(inp)
#     pd = {rows[0]: rows[1] for rows in reader}
#
# add_project_content(pd)

# filename = '../../example_data/import/dtakt_import.csv'
# df = pandas.read_csv(filename, sep=";")

# with open(filename, 'r', encoding="utf-8") as f:
#     df = pandas.read_csv(f)

filename = '../../example_data/import/subproject_bvwp.xlsx'
df = pandas.read_excel(filename)

PROJECT_GROUP_ID = 2

for index, pd in df.iterrows():
    add_project_content(pd, project_group_id=PROJECT_GROUP_ID)