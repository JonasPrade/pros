import networkx.exception
import os
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

dirname = os.path.dirname(__file__)
filepath_recalculate = os.path.realpath(os.path.join(dirname, '../../example_data/railgraph/recalculate_traingroups.json'))

with open(filepath_recalculate, 'r') as openfile:
    geojson_data = json.load(openfile)
    tgs = TimetableTrainGroup.query.filter(TimetableTrainGroup.id.in_(geojson_data["traingroups"])).all()

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

geojson_data["traingroups"] = []
with open(filepath_recalculate, "w") as outfile:
    json.dump(geojson_data, outfile)
