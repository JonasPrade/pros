import pandas
import logging

from prosd import db
from prosd.models import RailwayLine, TimetableTrainGroup, TimetableCategory
from prosd.graph import railgraph

from prosd.calculation_methods import use
from prosd.calculation_methods.cost import BvwpCost, BvwpCostElectrification, BvwpCostH2, BvwpProjectBattery, BvwpProjectEFuel


class Project:
    def __init__(self, railway_lines_id, traction_type, start_year_planning):
        """

        :param railway_lines: list of railway_lines that are part of the Project
        """

        # make five variants of that
        # electrification
        # battery
        # h2
        # eFuel
        # TODO: Think of an mixed variant electrification and battery
        self.railway_lines = RailwayLine.query.filter(RailwayLine.id.in_(railway_lines_id)).all()
        self.infrastructure_cost_base_year, self.start_year_operation, self.duration_operation = self.infrastructure_cost(
            traction_type=traction_type,
            start_year_planning=start_year_planning,
            railway_lines=self.railway_lines)
        self.use_sum, self.uses_dataframe = self.use_calculation(railway_lines_id=railway_lines_id, traction_type=traction_type)

        self.cost = self.use_sum + self.infrastructure_cost_base_year

    def use_calculation(self, railway_lines_id, traction_type):
        # get all TrainGroups that are running on this line
        train_groups = db.session.query(TimetableTrainGroup).join(RailwayLine.train_groups).filter(
            RailwayLine.id.in_(railway_lines_id)).all()

        # create dataframe for the results
        columns = ["traingroup/line", "use_sum", "capital_service", "maintenance_cost", "energy_cost"]
        uses_dataframe = pandas.DataFrame(columns=columns)

        # calculate the use for each train_group
        use_sum = 0
        black_list_train_group = []  # black list for spnv train_groups, because they get calculated as TimetableLine
        for train_group in train_groups:
            if train_group in black_list_train_group:
                continue
            else:
                transport_mode = train_group.category.transport_mode
                tg_use = None
                id = None
                try:
                    match transport_mode:
                        case "sgv":
                            tg_use = use.BvwpSgv(tg_id=train_group.id, traction=traction_type, start_year_operation=self.start_year_operation, duration_operation=self.duration_operation)
                            id = train_group.id
                        case "spfv":
                            tg_use = use.BvwpSpfv(tg_id=train_group.id, traction=traction_type, start_year_operation=self.start_year_operation, duration_operation=self.duration_operation)
                            id = train_group.id
                        case "spnv":
                            tt_line = train_group.traingroup_lines
                            for tg in tt_line.train_groups:
                                black_list_train_group.append(tg)
                            tg_use = use.StandiSpnv(trainline_id=tt_line.id, traction=traction_type, start_year_operation=self.start_year_operation, duration_operation=self.duration_operation)
                            id = tt_line.id
                except TypeError as e:
                    logging.error("For " + str(train_group) + " error at use calculation " + str(e))

                if tg_use:
                    use_sum +=tg_use.use_base_year

                    df = pandas.DataFrame(
                        [[id, tg_use.use_base_year, tg_use.debt_service_base_year, tg_use.maintenance_cost_base_year, tg_use.energy_cost_base_year]],
                        columns=columns
                    )
                else:
                    df = pandas.DataFrame(
                        [[id, 'ERROR', 'ERROR', 'ERROR', 'ERROR']]
                    )

                uses_dataframe = pandas.concat([uses_dataframe, df])

        return use_sum, uses_dataframe

    def infrastructure_cost(self, traction_type, start_year_planning, railway_lines):
        match traction_type:
            case 'electrification':
                infrastructure = BvwpCostElectrification(start_year_planning=start_year_planning, railway_lines=railway_lines)
            case 'h2':
                infrastructure = BvwpCostH2(start_year_planning=start_year_planning, railway_lines=railway_lines)
            case 'battery':
                infrastructure = BvwpProjectBattery(start_year_planning=start_year_planning, railway_lines=railway_lines)
            case 'efuel':
                infrastructure = BvwpProjectEFuel(start_year_planning=start_year_planning)
            case _:
                logging.error('traction_type not recognized')

        # capital_service_infrastructure = infrastructure.capital_service_cost_2015
        # maintenance_cost_infrastructure = infrastructure.maintenance_cost_2015
        start_year_operation = infrastructure.start_year_operation
        duration = infrastructure.DURATION_OPERATION
        infrastructure_cost_base_year = infrastructure.cost_2015

        # TODO: Implement Zuschlagfaktoren?

        return infrastructure_cost_base_year, start_year_operation, duration


if __name__ == "__main__":
    start = "NN"
    end = "NXSG"
    rg = railgraph.RailGraph()
    graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
    path = rg.shortest_path_between_stations(graph=graph, station_from=start, station_to=end)
    railway_lines = path["edges"]
    project = Project(railway_lines_id=railway_lines, traction_type='electrification', start_year_planning=2025)
    print(project.cost)
