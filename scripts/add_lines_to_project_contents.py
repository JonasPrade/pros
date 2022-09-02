from prosd import db
from prosd.models import RailwayLine, ProjectContent
from prosd.graph.railgraph import RailGraph

def add_lines_to_project_content(project_content_id, graph, from_station, to_station, via=[]):
    rg = RailGraph()
    path = rg.shortest_path_between_stations(graph=graph, station_from=from_station, station_to=to_station, stations_via=[])
    path_lines = path["edges"]

    ProjectContent.add_lines_to_pc(pc_id=project_content_id, lines=path_lines)


rg = RailGraph()
from_station = "HWOB"
to_station = "LNG"
via = []
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
project_content_id = 35


add_lines_to_project_content(project_content_id, graph, from_station, to_station, via=via)