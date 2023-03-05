import networkx.exception
import json

from prosd.models import TimetableTrainGroup, MasterScenario, RailwayLine, RouteTraingroup, TimetableTrain, TimetableTrainPart, TimetableCategory
import logging
from prosd import db
from prosd.graph import railgraph, routing
from prosd.manage_db import version

FORCE_RECALCULATION = True

rg = railgraph.RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
scenarios = [MasterScenario.query.get(4)]
# scenarios = MasterScenario.query.all()


# tgs = TimetableTrainGroup.query.join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
#     TimetableCategory.transport_mode=='spfv').all()

# tgs = TimetableTrainGroup.query.all()

tgs = [TimetableTrainGroup.query.get('tg_RP83_N_x0020_83002_x00A7__51849')]

logging.basicConfig(filename='../../example_data/railgraph/dtakt_routing.log', encoding='utf-8', level=logging.WARNING)

# print(tgs[0].trains[0].train_part.timetable_ocps)

for scenario in scenarios:
    infra_version = version.Version(scenario=scenario)
    route = routing.GraphRoute(graph=graph, infra_version=infra_version)
    for tg in tgs:
        try:
            route.line(traingroup=tg, force_recalculation=FORCE_RECALCULATION)
            ocp = tg.trains[0].train_part.timetable_ocps
        except (UnboundLocalError, networkx.exception.NodeNotFound) as e:
            logging.error(f"{e.args} {tg}")


