import os
import json

from prosd.graph import railgraph
from prosd.models import RailwayRoute

route_number = 1711
route = RailwayRoute.query.filter(RailwayRoute.number == route_number).scalar()

rg = railgraph.RailGraph()

graph = rg.create_graph_one_route(route=route)
print(graph)
