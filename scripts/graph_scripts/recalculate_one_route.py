import os
import json

from prosd.graph import railgraph
from prosd.models import RailwayRoute

dirname = os.path.dirname(__file__)
filepath_recalculate = os.path.realpath(os.path.join(dirname, '../../example_data/railgraph/recalculate_traingroups.json'))

with open(filepath_recalculate, 'r') as openfile:
    geojson_data = json.load(openfile)

routes = []
for route in geojson_data["routes"]:
    routes.append(RailwayRoute.query.filter(RailwayRoute.number == route).scalar())

# route = [RailwayRoute.query.filter(RailwayRoute.number == 1105).scalar()]

rg = railgraph.RailGraph()
for route in routes:
    graph = rg.create_graph_one_route(route=route)
    print(graph)


geojson_data["routes"] = []
with open(filepath_recalculate, "w") as outfile:
    json.dump(geojson_data, outfile)
