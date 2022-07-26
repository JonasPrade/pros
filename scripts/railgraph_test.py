from prosd.graph.railgraph import RailGraph, models
import logging
import networkx
import matplotlib.pyplot as pyplot

logging.basicConfig(filename='/Users/jonas/PycharmProjects/pros/prosd/log/log_creating_railgraph.log', encoding='utf-8', level=logging.WARNING)

rg = RailGraph()
# rg.combine_nodes(225008, 70970)
# rg.create_nodes_new_railwaylines()

# test create graph
rg.create_graph(new_nodes=False)

# # test create graph route for one route
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 1240).first()
# graph_list = rg.create_graph_route(route=route)
# graph = graph_list[0]

# pyplot.figure(3, figsize=(12,12))
# networkx.draw_networkx(graph, with_labels=True, node_size=100)
# pyplot.show()
# networkx.dijkstra_path(graph, 531176457751, 223816457810)
# networkx.dijkstra_path(graph, 531176457751, 149650468530)

# # test create turner
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number==1255).first()
# graph_list = rg.create_graph_route(route=route)
# graph = graph_list[0]
# node = models.RailwayNodes.query.filter(models.RailwayNodes.id==268413).one()
# networkx.dijkstra_path(graph, 531176, 223816)
# networkx.dijkstra_path(graph, 531176, 149650)
# graph = rg._create_turner(G=graph, node_input=node)
#
# networkx.dijkstra_path(graph, 531176, 223816)
# networkx.dijkstra_path(graph, 531176, 149650)


# # test node with more than two edges
# node = models.RailwayNodes.query.filter(models.RailwayNodes.id == 325375).one()
# node_lines = []
# node_lines.append(node.start_node)
# node_lines.append(node.end_node)
# logging.info('finished creating Graph')





