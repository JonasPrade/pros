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
scenario = MasterScenario.query.get(2)
version = version.Version(scenario=scenario)

route = routing.GraphRoute(graph=graph, infra_version=version)


# tgs = TimetableTrainGroup.query.join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
#     TimetableCategory.transport_mode=='spfv').all()

tgs = TimetableTrainGroup.query.all()

# tgs = TimetableTrainGroup.query.get('tg_141_x0020_G_x0020_2554_104157')

# logging.basicConfig(filename='../../example_data/railgraph/dtakt_routing.log', encoding='utf-8', level=logging.WARNING)

if isinstance(tgs, list):
    for tg in tgs:
        if len(tg.railway_lines) == 0:
            try:
                route.line(traingroup=tg, force_recalculation=FORCE_RECALCULATION)
                ocp = tg.trains[0].train_part.timetable_ocps
            except (UnboundLocalError, networkx.exception.NodeNotFound) as e:
                logging.error(f"{e.args} {tg}")
else:
    route.line(traingroup=tgs, force_recalculation=FORCE_RECALCULATION)
    ocps = tgs.trains[0].train_part.timetable_ocps

