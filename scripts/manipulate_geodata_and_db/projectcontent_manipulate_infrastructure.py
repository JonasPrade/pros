import pandas

from prosd.models import RailwayLine, RailwayStation, ProjectContent
from prosd.calculation_methods.bvwp_project import Project
from prosd.graph import railgraph

def create_railway_lines_df():
    columns = ['railway_line_id', 'railway_line_model']
    railway_lines = RailwayLine.query.with_entities(RailwayLine.id, RailwayLine).order_by(RailwayLine.id).all()
    railway_lines_df = pandas.DataFrame(railway_lines, columns=columns)

    return railway_lines_df

def change_electrification(project_content, railway_line):
    if project_content.elektrification:
        railway_line.electrified = True
        railway_line.catenary = True
        railway_line.voltage = 15
        railway_line.dc_ac = 'ac'

    return railway_line


active_project_content_id = [
85
]

active_project_contents = ProjectContent.query.filter(ProjectContent.id.in_(active_project_content_id)).all()

railway_lines_df = create_railway_lines_df()
columns = ['railway_line_id', 'railway_line_model']

for pc in active_project_contents:
    pc_r_lines = pc.projectcontent_railway_lines
    for line in pc_r_lines:
        rl_changed = railway_lines_df[railway_lines_df.railway_line_id == line.id]["railway_line_model"].iloc[0]
        railway_lines_df = railway_lines_df[railway_lines_df.railway_line_id != line.id]
        rl_changed = change_electrification(project_content=pc, railway_line=rl_changed)
        # TODO: Change more settings

        rl_df = pandas.DataFrame([[line.id, rl_changed]], columns=columns)
        railway_lines_df = pandas.concat([railway_lines_df, rl_df])


start = "NN"
end = "NXSG"
rg = railgraph.RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
path = rg.shortest_path_between_stations(graph=graph, station_from=start, station_to=end)
railway_lines_original = path["edges"]
railway_lines_id = railway_lines_df[railway_lines_df["railway_line_id"].isin(railway_lines_original)]
project = Project(railway_lines_df=railway_lines_id, traction_type="electrification", start_year_planning=2025)
print(project.cost)
