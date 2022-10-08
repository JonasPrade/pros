import pandas
import logging

from prosd import db
from prosd.models import RailwayLine, TimetableTrainGroup, TimetableCategory
from prosd.graph import railgraph

from prosd.calculation_methods import bvwp

class BvwpProject:
    def __init__(self, railway_lines):
        """

        :param railway_lines: list of railway_lines that are part of the Project
        """

        # make five variants of that
        # electrification
        # battery
        # h2
        # eFuel
        # Bezugsfall
        # TODO: Think of an mixed variant electrification and battery

        # get all TrainGroups that are running on this line
        train_groups = db.session.query(TimetableTrainGroup).join(RailwayLine.train_groups).filter(
            RailwayLine.id.in_(railway_lines)).all()

        columns=["traingroup","reference_case", "electrification", "battery", "h2", "efuel"]
        traingroups_use = pandas.DataFrame(columns=columns)
        for train_group in train_groups:
            transport_mode = train_group.category.transport_mode
            tg_use = None
            try:
                match transport_mode:
                    case "sgv":
                        tg_use = bvwp.BvwpSgv(tg_id=train_group.id)
                    case "spfv":
                        tg_use = bvwp.BvwpSpfv(tg_id=train_group.id)
                    case "spnv":
                        tg_use = bvwp.BvwpSpnv(tg_id=train_group.id)
            except TypeError as e:
                logging.error("For " + str(train_group) + " error at use calculation " + str(e))

            if tg_use:
                use_reference_case = tg_use.use
                # cases for electrification etc.
                use_electrification = 0
                use_battery = 0
                use_h2 = 0
                use_efuel = 0

                # TODO: For that: Get a table that names a alternative for all diesel-trains for each possible case!

                use_series = pandas.DataFrame(
                    [[train_group.id, use_reference_case, use_electrification, use_battery, use_h2, use_efuel]],
                    columns=columns
                    )
                traingroups_use = pandas.concat([traingroups_use, use_series])

        print(traingroups_use)

        # for the infrastructure cost create project_content and calculate the costs
        # TODO: Create class or function that can calculate the cost of electrification, battery, h2 (eFuel no new infrastructure cost?)

        # alway calculate the bezugsfall and than on planfall case? Nope


if __name__ == "__main__":
    start = "NN"
    end = "NXSG"
    rg = railgraph.RailGraph()
    graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
    path = rg.shortest_path_between_stations(graph=graph, station_from=start, station_to=end)
    railway_lines = path["edges"]
    BvwpProject(railway_lines=railway_lines)
