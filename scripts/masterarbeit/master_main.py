import logging
import sqlalchemy

from prosd import db
from prosd.models import TimetableTrainGroup, TimetableTrain, RailwayLine, RouteTraingroup, TimetableCategory, TimetableTrainPart, MasterScenario, MasterArea
from prosd.calculation_methods import use, cost

scenario_id = 1
areas = MasterArea.query.filter(MasterArea.scenario_id==scenario_id).all()


def calc_train_cost(traction, areas):
    train_cost_electrification = dict()
    whitelist_traingroup = []
    for tg in areas.traingroups:
        if tg in whitelist_traingroup:
            continue

        try:
            match tg.category.transport_mode:
                case "sgv":
                    train_cost = use.BvwpSgv(tg_id=tg.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction)
                case "spfv":
                    if traction == "efuel":
                        # in this case, bvwp does not provide any vehicles
                        trainline = tg.traingroup_lines
                        whitelist_traingroup += trainline.train_groups
                        train_cost = use.StandiSpnv(trainline_id=trainline.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction)
                    else:
                        train_cost = use.BvwpSpfv(tg_id=tg.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction)
                case "spnv":
                    # get the trainline and add all train_groups of that line to the whitelist
                    trainline = tg.traingroup_lines
                    whitelist_traingroup += trainline.train_groups
                    train_cost = use.StandiSpnv(trainline_id=trainline.id, start_year_operation=start_year, duration_operation=duration_operation, traction=traction)
        except use.NoVehiclePatternExistsError as e:
            logging.error(f"For {tg} no train cost calculation possible {e}")


        train_cost_electrification[tg.id] = train_cost.use_base_year

    return train_cost_electrification


for cluster_id, areas in enumerate(areas):
    start_year_planning = 2025  # TODO: get start_year_planning and start_year of operation united
    start_year = 2030
    duration_operation = 30

    # # electrification
    traction = 'electrification'

    train_cost_electrification = calc_train_cost(traction=traction, areas=areas)

    infrastructure_cost_electrification = cost.BvwpCostElectrification(
        start_year_planning=start_year_planning,
        railway_lines=areas.railway_lines,
        abs_nbs='abs'
    )

    electrification_dict = dict()
    electrification_dict["electrification_cost"] = sum(train_cost_electrification.values()) + infrastructure_cost_electrification.cost_2015
    electrification_dict["electrification_infrastructure_cost"] = infrastructure_cost_electrification.cost_2015
    electrification_dict["electrification_train_cost"] = train_cost_electrification


    logging.info(f"finished calculation electrification {cluster_id}")

    ## efuel
    traction = 'efuel'

    train_cost_efuel = calc_train_cost(traction=traction, areas=areas)

    infrastructure_cost_efuel = 0  # for efuel there are no infrastructure costs

    efuel_dict = dict()
    efuel_dict["efuel_cost"] = sum(
        train_cost_efuel.values()) + infrastructure_cost_efuel
    efuel_dict["efuel_infrastructure_cost"] = infrastructure_cost_efuel
    efuel_dict["efuel_train_cost"] = train_cost_efuel


    logging.info(f"finished calculation efuel {cluster_id}")

    ## h2?

    if areas["electrification"]["electrification_cost"] <= areas['efuel']['efuel_cost']:
        areas["traction_decision"] = "electrification"
        # TODO: Create project_content for the elctrification and add it to specific version
    else:
        areas["traction_decision"] = "efuel"

    print(f"{cluster_id} {areas['traction_decision']} – electrification {areas['electrification']['electrification_cost']}; efuel {areas['efuel']['efuel_cost']}")



