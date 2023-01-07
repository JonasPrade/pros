import logging
import sqlalchemy

from prosd import db, parameter
from prosd.models import TimetableTrainGroup, TimetableTrain, RailwayLine, RouteTraingroup, TimetableCategory, TimetableTrainPart, MasterScenario, MasterArea, TimetableTrainCost
from prosd.calculation_methods import use, cost, base

scenario_id = 1
areas = MasterArea.query.filter(MasterArea.scenario_id==scenario_id).all()
base = base.BaseCalculation()


def calc_train_cost(traction, area):
    trains_cost = dict()

    for tg in area.traingroups:
        ttc = TimetableTrainCost.query.filter(
            TimetableTrainCost.traingroup_id == tg.id,
            TimetableTrainCost.calculation_method == 'bvwp',
            TimetableTrainCost.master_scenario_id == 1,
            TimetableTrainCost.traction == traction
        ).scalar()

        if ttc is None:
            ttc = TimetableTrainCost.query.filter(
                TimetableTrainCost.traingroup_id == tg.id,
                TimetableTrainCost.calculation_method == 'standi',
                TimetableTrainCost.master_scenario_id == 1,
                TimetableTrainCost.traction == traction
            ).scalar()

        if ttc is None:
            ttc = TimetableTrainCost.create(
                traingroup=tg,
                master_scenario_id=1,
                traction=traction
            )

        trains_cost[tg.id] = base.cost_base_year(start_year=start_year, duration=duration_operation, cost=ttc.cost)


        # try:
        #     match tg.category.transport_mode:
        #         case "sgv":
        #             train_cost = tg.get_cost_by_traction(obj=tg, traction=traction)
        #             if train_cost is None:
        #                 train_cost = use.BvwpSgv(tg_id=tg.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction).use
        #         case "spfv":
        #             if traction == "efuel":
        #                 # in this case, bvwp does not provide any vehicles
        #                 trainline = tg.traingroup_lines
        #                 whitelist_traingroup += trainline.train_groups
        #                 train_cost = tg.get_cost_by_traction(obj=tg, traction=traction)
        #                 if train_cost is None:
        #                     train_cost = use.StandiSpnv(trainline_id=trainline.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction).use
        #             else:
        #                 train_cost = tg.get_cost_by_traction(obj=tg, traction=traction)
        #                 if train_cost is None:
        #                     train_cost = use.BvwpSpfv(tg_id=tg.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction).use
        #         case "spnv":
        #             # get the trainline and add all train_groups of that line to the whitelist
        #             trainline = tg.traingroup_lines
        #             whitelist_traingroup += trainline.train_groups
        #             train_cost = tg.get_cost_by_traction(obj=tg, traction=traction)
        #             if train_cost is None:
        #                 train_cost = use.StandiSpnv(trainline_id=trainline.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction).use
        # except use.NoVehiclePatternExistsError as e:
        #     logging.error(f"For {tg} no train cost calculation possible {e}")
        #
        # train_cost_electrification[tg.id] = base.cost_base_year(start_year=start_year, duration=duration_operation, cost=train_cost)

    return trains_cost


for cluster_id, area in enumerate(areas):
    start_year_planning = parameter.START_YEAR - parameter.DURATION_PLANNING  # TODO: get start_year_planning and start_year of operation united
    start_year = parameter.START_YEAR
    duration_operation = parameter.DURATION_OPERATION

    # electrification
    traction = 'electrification'
    train_cost_electrification = calc_train_cost(traction=traction, area=area)
    infrastructure_cost_electrification = cost.BvwpCostElectrification(
        start_year_planning=start_year_planning,
        railway_lines=area.railway_lines,
        abs_nbs='abs'
    )
    logging.info(f"finished calculation electrification {cluster_id}")

    # efuel
    traction = 'efuel'
    train_cost_efuel = calc_train_cost(traction=traction, area=area)
    infrastructure_cost_efuel = 0  # for efuel there are no infrastructure costs
    logging.info(f"finished calculation efuel {cluster_id}")

    # h2
