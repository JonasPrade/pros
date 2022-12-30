from prosd.graph.railgraph import RailGraph

station_from = "HIHG"
station_to = "HLTA"

rg = RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)

path = rg.shortest_path_between_stations(graph=graph, station_from=station_from, station_to=station_to)

