import logging
import sqlalchemy

from prosd import db
from prosd.models import TimetableTrainGroup, TimetableTrain, RailwayLine, RouteTraingroup, TimetableCategory, TimetableTrainPart
from prosd.calculation_methods import use, cost


def calc_train_cost(traction, cluster):
    train_cost_electrification = dict()
    whitelist_traingroup = []
    for tg in cluster["traingroups"]:
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


#############

sgv_lines = db.session.query(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(RouteTraingroup).join(TimetableCategory).join(RailwayLine).filter(
    sqlalchemy.and_(
    RailwayLine.catenary==False,
    TimetableCategory.transport_mode == 'sgv'
)).all()

# TODO: Need system to remove all used traingroups

# a list that contains the collected traingroups
traingroup_clusters = dict()

# TODO: Routing is not perfect, routes sometimes unneccessary via not electrified routes
# whitelist = [
# 'tg_207_x0020_G_x0020_2503_69529',
# ]

# TODO: Have to use a version of lines, not the lines itself!

while sgv_lines:
    # take the first sgv_traingroup of the list and remove it from the list. Get also the railway_lines of that traingroup
    traingroups = list()
    rw_lines = list()
    sgv_line = sgv_lines.pop(0)
    traingroups.append(sgv_line)

    # if sgv_line.id in whitelist:
    #     continue

    length_rl_lines = sum(int(r.length) for r in rw_lines)

    # search for all lines that share a unelectrified railway_line witht the sgv_line
    delta_traingroups = True
    while delta_traingroups is True:
        rl_lines_additional = db.session.query(RailwayLine).join(RouteTraingroup).join(TimetableTrainGroup).filter(
            sqlalchemy.and_(
                RailwayLine.catenary == False,
                TimetableTrainGroup.id.in_([t.id for t in traingroups]),
                RailwayLine.id.notin_([r.id for r in rw_lines])
            )).all()

        if rl_lines_additional:
            rw_lines = rw_lines + rl_lines_additional

        traingroups_additional = db.session.query(TimetableTrainGroup).join(RouteTraingroup).join(RailwayLine).filter(
        sqlalchemy.and_(
            RailwayLine.catenary==False,
            RailwayLine.id.in_([r.id for r in rw_lines]),
            TimetableTrainGroup.id.notin_([t.id for t in traingroups])
    )).all()

        if traingroups_additional:
            traingroups = traingroups + traingroups_additional
        else:
            delta_traingroups = False

    # Remove used sgv lines from the sgv_lines
    for tg in traingroups:
        if tg.category.transport_mode == 'sgv' and tg is not sgv_line:
            sgv_lines.remove(tg)

    # add the traingroups as a collected group to the traingroup_cluster
    traingroup_clusters[str(len(traingroup_clusters)+1)] = {"traingroups": traingroups, "railway_lines": rw_lines}

logging.info('finished grouping trains')

for cluster_id, cluster in traingroup_clusters.items():
    start_year_planning = 2025  # TODO: get start_year_planning and start_year of operation united
    start_year = 2030
    duration_operation = 30

    # # electrification
    traction = 'electrification'

    train_cost_electrification = calc_train_cost(traction=traction, cluster=cluster)

    infrastructure_cost_electrification = cost.BvwpCostElectrification(
        start_year_planning=start_year_planning,
        railway_lines=cluster["railway_lines"],
        abs_nbs='abs'
    )

    electrification_dict = dict()
    electrification_dict["electrification_cost"] = sum(train_cost_electrification.values()) + infrastructure_cost_electrification.cost_2015
    electrification_dict["electrification_infrastructure_cost"] = infrastructure_cost_electrification.cost_2015
    electrification_dict["electrification_train_cost"] = train_cost_electrification
    cluster["electrification"] = electrification_dict

    logging.info(f"finished calculation electrification {cluster_id}")

    ## efuel
    traction = 'efuel'

    train_cost_efuel = calc_train_cost(traction=traction, cluster=cluster)

    infrastructure_cost_efuel = 0  # for efuel there are no infrastructure costs

    efuel_dict = dict()
    efuel_dict["efuel_cost"] = sum(
        train_cost_efuel.values()) + infrastructure_cost_efuel
    efuel_dict["efuel_infrastructure_cost"] = infrastructure_cost_efuel
    efuel_dict["efuel_train_cost"] = train_cost_efuel
    cluster["efuel"] = efuel_dict

    logging.info(f"finished calculation efuel {cluster_id}")

    ## h2?

    if cluster["electrification"]["electrification_cost"] <= cluster['efuel']['efuel_cost']:
        cluster["traction_decision"] = "electrification"
        # TODO: Create project_content for the elctrification and add it to specific version
    else:
        cluster["traction_decision"] = "efuel"

    print(f"{cluster_id} {cluster['traction_decision']} – electrification {cluster['electrification']['electrification_cost']}; efuel {cluster['efuel']['efuel_cost']}")



