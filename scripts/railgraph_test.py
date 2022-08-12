from prosd.graph.railgraph import RailGraph, models
import logging
import networkx
import matplotlib.pyplot as pyplot
import shapely

logging.basicConfig(filename='/Users/jonas/PycharmProjects/pros/prosd/log/log_creating_railgraph.log', encoding='utf-8', level=logging.WARNING)

rg = RailGraph()
# rg.combine_nodes(225008, 70970)
# rg.create_nodes_new_railwaylines()

# test create graph
graph = rg.create_graph(new_nodes=False)
print(graph)

# test create graph route for one route


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

# # test remove railline from graph
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 4950).one()
# graph_list = rg.create_graph_route(route=route)
# graph = graph_list[0]
# line = models.RailwayLine.query.filter(models.RailwayLine.id == 39552).one()
# graph = rg._remove_line_from_graph(G=graph, line=line)
# graph = rg._add_line_to_graph(G=graph, line=line)

# # test connect_end_node_to_line
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 4950).one()
# graph_list = rg.create_graph_route(route=route)
# graph_continuing = graph_list[0]
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 4930).one()
# graph_list = rg.create_graph_route(route=route)
# graph_of_node = graph_list[0]

# node = models.RailwayNodes.query.get(290586)
# line_of_node = models.RailwayLine.query.get(39515)
# graph = rg._connect_end_node_to_line(G_continuing_line=graph_continuing, G_of_node=graph_of_node, node=node, line_of_node=line_of_node)
# print(graph)


