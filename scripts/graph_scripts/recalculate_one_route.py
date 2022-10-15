from prosd.graph import railgraph
from prosd.models import RailwayRoute

route = RailwayRoute.query.filter(RailwayRoute.number == 4850).scalar()

rg = railgraph.RailGraph()
graph = rg.create_graph_one_route(route=route)
print(graph)
