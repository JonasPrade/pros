from prosd.graph.railgraph import RailGraph

rg = RailGraph()
graph = rg.load_graph(filepath=rg.filepath_save_with_station_and_parallel_connections)
rg.draw_map(graph=graph)