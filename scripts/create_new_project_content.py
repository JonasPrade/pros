from prosd import db
from prosd.models import ProjectContent, Project
import csv

# import project_content.csv als Datenquelle
filename = '../example_data/project_content_import/project_content.csv'

with open(filename, mode='r') as inp:
    reader = csv.reader(inp)
    pd = {rows[0]: rows[1] for rows in reader}

project = Project(
    name=pd["project_name"]
)
db.session.add(project)
db.session.commit()
db.session.refresh(project)


# TODO: Add estimated cost
pc = ProjectContent(
    project_id=project.id,
    project_number=pd["project_number"],
    name=pd["pc_name"],
    description=pd["pc_description"],
    reason_project=pd["pc_reason"],
    effects_passenger_long_rail=bool(int(pd["effect_long_rail"])),
    effects_passenger_local_rail=bool(int(pd["effect_local_rail"])),
    effects_cargo_rail=bool(int(pd["effect_cargo"])),
    nbs=bool(int(pd["nbs"])),
    abs=bool(int(pd["abs"])),
    elektrification=bool(int(pd["elektrification"])),
    batterie=bool(int(pd["batterie"])),
    second_track=bool(int(pd["second_track"])),
    third_track=bool(int(pd["third_track"])),
    fourth_track=bool(int(pd["fourth_track"])),
    curve=bool(int(pd["curve"])),
    platform=bool(int(pd["platform"])),
    junction_station=bool(int(pd["junction_station"])),
    number_junction_station=int(pd["number_junction_station"]),
    overtaking_station=bool(int(pd["overtaking_station"])),
    number_overtaking_station=int(pd["number_overtaking_station"]),
    double_occupancy=bool(int(pd["double_occupancy"])),
    block_increase=bool(int(pd["block_increase"])),
    flying_junction=bool(int(pd["flying_junction"])),
    tunnel_structural_gauge=bool(int(pd["tunnel_structural_gauge"])),
    increase_speed=bool(int(pd["increase_speed"])),
    new_vmax=int(pd["new_vmax"]),
    level_free_platform_entrance=bool(int(pd["level_free_platform_entrance"])),
    etcs=bool(int(pd["etcs"])),
    etcs_level=int(pd["etcs_level"])
)
db.session.add(pc)
db.session.commit()

# TODO: railway_lines
# TODO: constituencies
# TODO: counties
# TODO: states
