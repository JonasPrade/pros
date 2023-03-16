from prosd.graph import railgraph, routing
from prosd.models import MasterScenario
from prosd.manage_db import version
import networkx

station_from = "TEST3"
station_to = "WVE"

rg = railgraph.RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
scenario = MasterScenario.query.get(4)
version = version.Version(scenario=scenario)

route = routing.GraphRoute(graph=graph, infra_version=version)

path = route.route_line(station_from=station_from, station_to=station_to, stations_via=[], save_route=True)

print(path)
