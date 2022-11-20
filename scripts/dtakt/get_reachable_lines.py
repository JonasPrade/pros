import pandas

from prosd.graph.railgraph import RailGraph
from prosd.graph.routing import GraphRoute
from prosd.models import RailwayLine

start_station = 'TS'
allowed_distance = 70

columns = ['railway_line_id', 'railway_line_length']
railway_lines = RailwayLine.query.with_entities(RailwayLine.id, RailwayLine.length).order_by(RailwayLine.id).all()
railway_lines_df = pandas.DataFrame(railway_lines, columns=columns)

rg = RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)

routing = GraphRoute(graph=graph, railway_lines_df=railway_lines_df)
line_ids = routing.reachable_lines(start_station=start_station, allowed_distance=allowed_distance)
print(line_ids)