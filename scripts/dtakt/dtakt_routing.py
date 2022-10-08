import networkx.exception

from prosd.models import TimetableTrain, TimetableTrainPart, TimetableOcp, TimetableTrainGroup, RailwayLine
import logging
from prosd import db
from prosd.graph import railgraph

rg = railgraph.RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
tgs = TimetableTrainGroup.query.all()
# tgs = TimetableTrainGroup.query.filter(TimetableTrainGroup.id == "tg_FV17.a_x0020_C_x0020_17101_6904").all()
logging.basicConfig(filename='../../example_data/railgraph/dtakt_routing.log', encoding='utf-8', level=logging.WARNING)

objects = []
missing_stations = set()

for tg in tgs:

    if len(tg.lines) == 0:
        train = tg.trains[0]

        # find first ocp
        try:
            first_ocp = train.train_part.first_ocp.ocp.station.db_kuerzel
        except AttributeError:
            logging.warning("TrainGroup " + str(tg.id) + " first ocp not existing in railway_station " + str(train.train_part.first_ocp.ocp.name) + " " + str(train.train_part.first_ocp.ocp.code))
            missing_stations.add(train.train_part.first_ocp.ocp.name)
            continue

        # find last ocp
        try:
            last_ocp = train.train_part.last_ocp.ocp.station.db_kuerzel
        except AttributeError:
            logging.warning("TrainGroup " + str(tg.id) + " last ocp not existing in railway_station " + str(train.train_part.last_ocp.ocp.name) + " " + str(train.train_part.last_ocp.ocp.code))
            missing_stations.add(train.train_part.last_ocp.ocp.name)
            continue

        # route the via stations (check if they exist)
        via = []
        for tt_ocp in train.train_part.timetable_ocps[1:-1]:
            try:
                station = tt_ocp.ocp.station.db_kuerzel
                via.append(station)
            except AttributeError:
                logging.info("In train_group" + str(tg.id) + "tt_ocp " + str(tt_ocp) + " " + str(tt_ocp.ocp.code) + " has no fitting railway_station")
                continue

        # route the traingroup
        try:
            path = rg.shortest_path_between_stations(graph=graph, station_from=first_ocp, station_to=last_ocp, stations_via = via)
        except networkx.exception.NetworkXNoPath:
            logging.warning("No path found for traingroup " + str(tg.id) + " from " + str(first_ocp) + " to " + str(last_ocp))
            continue

        lines = RailwayLine.query.filter(RailwayLine.id.in_(path["edges"])).all()
        tg.lines = lines

        objects.append(tg)

db.session.bulk_save_objects(objects)
db.session.commit()
