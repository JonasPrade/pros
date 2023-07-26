import pandas
import logging

from prosd.models import RailwayLine, ProjectContent
from prosd.graph.railgraph import RailGraph


def add_lines_to_project_content(project_content_id, graph, from_station, to_station, via=[]):
    rg = RailGraph()
    path = rg.shortest_path_between_stations(graph=graph, station_from=from_station, station_to=to_station, stations_via=via)
    path_lines = path["edges"]

    ProjectContent.add_lines_to_pc(pc_id=project_content_id, lines=path_lines)


def read_excel(filepath):
    df = pandas.read_excel(filepath, usecols='A:C')
    return df


filepath = '../../example_data/import/lines_to_projects/hlk.xlsx'
df = read_excel(filepath)
rg = RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)

for index, data in df.iterrows():
    try:
        add_lines_to_project_content(project_content_id=data.iloc[0], graph=graph, from_station=data.iloc[1], to_station=data.iloc[2])
    except Exception as e:
        logging.error(f"Error at {data.iloc[0]}: {e}")

#
# rg = RailGraph()
# from_station = "NAS"
# to_station = "NBOE"
# via = []
# graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
# project_content_id = 380
#
#
# add_lines_to_project_content(project_content_id, graph, from_station, to_station, via=via)
