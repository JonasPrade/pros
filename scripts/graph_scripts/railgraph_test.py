from prosd.graph.railgraph import RailGraph, models
import logging
import networkx
import matplotlib.pyplot as pyplot
import shapely
from prosd import db
import geoalchemy2

# logging.basicConfig(filename='/prosd/log/log_creating_railgraph.log', encoding='utf-8', level=logging.WARNING)

rg = RailGraph()
# rg.combine_nodes(225008, 70970)
# rg.create_nodes_new_railwaylines()

# # test create manipulate_geodata_and_db
# manipulate_geodata_and_db = rg.create_graph(new_nodes=False, use_saved=True)
# print(manipulate_geodata_and_db)


# manipulate_geodata_and_db = rg.load_graph(rg.filepath_save_with_station)
# station = models.RailwayStation.query.get(592)
# rg.create_connection_parallel_lines_one_station(manipulate_geodata_and_db=manipulate_geodata_and_db, station=station)
# # graph_new = rg.create_connection_parallel_lines(manipulate_geodata_and_db=manipulate_geodata_and_db)
# print(manipulate_geodata_and_db)

# # # test point
# rg.create_nodes_new_railwaylines()

# filepath = '../example_data/railgraph_test/railgraph_with_station.pickle'
# manipulate_geodata_and_db = rg.load_graph(filepath)
#
# nodes_missing_nodes_id = []
# for n in manipulate_geodata_and_db.nodes(data=True):
#     try:
#         if n[1]["node_id"]:
#             continue
#     except KeyError:
#         nodes_missing_nodes_id.append(n)


# # # # test create manipulate_geodata_and_db route for one route
route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 9122).scalar()
graph = rg.create_graph_one_route(route=route)
print(graph)

# line = models.RailwayLine.query.get(47878)
# manipulate_geodata_and_db = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
# path = rg.shortest_path_between_stations(manipulate_geodata_and_db, "TS", "BL")
# print(path)

# pyplot.figure(3, figsize=(12,12))
# networkx.draw_networkx(manipulate_geodata_and_db, with_labels=True, node_size=100)
# pyplot.show()
# networkx.dijkstra_path(manipulate_geodata_and_db, 531176457751, 223816457810)
# networkx.dijkstra_path(manipulate_geodata_and_db, 531176457751, 149650468530)

# # test create turner
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number==1255).first()

# node = models.RailwayNodes.query.filter(models.RailwayNodes.id==268413).one()
# networkx.dijkstra_path(manipulate_geodata_and_db, 531176, 223816)
# networkx.dijkstra_path(manipulate_geodata_and_db, 531176, 149650)
# manipulate_geodata_and_db = rg._create_turner(G=manipulate_geodata_and_db, node_input=node)
#
# networkx.dijkstra_path(manipulate_geodata_and_db, 531176, 223816)
# networkx.dijkstra_path(manipulate_geodata_and_db, 531176, 149650)

# # test node with more than two edges
# node = models.RailwayNodes.query.filter(models.RailwayNodes.id == 325375).one()
# node_lines = []
# node_lines.append(node.start_node)
# node_lines.append(node.end_node)
# logging.info('finished creating Graph')

# # test remove railline from manipulate_geodata_and_db
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 4950).one()
# graph_list = rg.create_graph_route(route=route)
# manipulate_geodata_and_db = graph_list[0]
# line = models.RailwayLine.query.filter(models.RailwayLine.id == 39552).one()
# manipulate_geodata_and_db = rg._remove_line_from_graph(G=manipulate_geodata_and_db, line=line)
# manipulate_geodata_and_db = rg._add_line_to_graph(G=manipulate_geodata_and_db, line=line)

# # test connect_end_node_to_line
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 4950).one()
# graph_list = rg.create_graph_route(route=route)
# graph_continuing = graph_list[0]
# route = models.RailwayRoute.query.filter(models.RailwayRoute.number == 4930).one()
# graph_list = rg.create_graph_route(route=route)
# graph_of_node = graph_list[0]

# node = models.RailwayNodes.query.get(290586)
# line_of_node = models.RailwayLine.query.get(39515)
# manipulate_geodata_and_db = rg._connect_end_node_to_line(G_continuing_line=graph_continuing, G_of_node=graph_of_node, node=node, line_of_node=line_of_node)
# print(manipulate_geodata_and_db)

# #
# old_line_id = 16833
# coordinate = models.RailwayPoint.query.get(46504).coordinates
# models.RailwayLine.split_railwayline(old_line_id=old_line_id, blade_point=coordinate)
# #
# blade_point=models.RailwayNodes.query.get(214512).coordinate
# models.RailwayLine.split_railwayline(old_line_id=47894, blade_point=blade_point)

#
# # geometry type check
# lines = models.RailwayLine.query.all()
#
# count_z = 0
#
# for line in lines:
#     coordinates = line.coordinates
#     coordinates_2d = db.session.execute(
#         db.select(
#             geoalchemy2.func.ST_Force2D(coordinates)
#         )
#     ).scalar()
#
#     line.coordinates = coordinates_2d
#
#     db.session.add(line)
#     db.session.commit()
#
# print(count_z)


# ## shortest path
# manipulate_geodata_and_db = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
# path = rg.shortest_path_between_stations(manipulate_geodata_and_db, "TS", "UWM", stations_via=['NBA', 'NC'])