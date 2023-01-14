import logging
import sqlalchemy

from prosd import db, parameter
from prosd.models import ProjectContent, MasterArea, TimetableTrainCost
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
            try:
                ttc = TimetableTrainCost.create(
                    traingroup=tg,
                    master_scenario_id=1,
                    traction=traction
                )
            except use.NoVehiclePatternExistsError as e:
                logging.error(e)
                continue

        trains_cost[tg.id] = base.cost_base_year(start_year=start_year, duration=duration_operation, cost=ttc.cost)

    return trains_cost


def infrastructure_cost(area, name, traction, overwrite=True):
    """
    Creates a project_content object and adds it to the db.
    :return:
    """
    pc = ProjectContent.query.filter(ProjectContent.name == name).scalar()
    if pc and overwrite is False:
        return pc
    elif pc and overwrite is True:
        db.session.delete(pc)
        db.session.commit()  # and calculate a new project_content

    if traction == "electrification":
        infrastructure_cost = cost.BvwpCostElectrification(
            start_year_planning=start_year_planning,
            railway_lines=area.railway_lines,
            abs_nbs='abs'
        )
    else:
        logging.error(f"no fitting traction found for {traction}")
        return None

    pc_data = dict()

    pc_data["name"] = name
    pc_data["master_areas"] = [area]
    #TODO Add description

    if 'spfv' in area.categories:
        pc_data["effects_passenger_long_rail"] = True
    else:
        pc_data["effects_passenger_long_rail"] = False

    if 'spnv' in area.categories:
        pc_data["effects_passenger_local_rail"] = True
    else:
        pc_data["effects_passenger_local_rail"] = False

    if 'sgv' in area.categories:
        pc_data["effects_cargo_rail"] = True
    else:
        pc_data["effects_cargo_rail"] = False

    pc_data["length"] = infrastructure_cost.length

    if traction == 'electrification':
        pc_data["elektrification"] = True
        # TODO: Add battery project_contents

    pc_data["planned_total_cost"] = infrastructure_cost.cost_2015
    pc_data["maintenance_cost"] = infrastructure_cost.maintenance_cost_2015
    pc_data["planning_cost"] = infrastructure_cost.planning_cost_2015
    pc_data["investment_cost"] = infrastructure_cost.investment_cost_2015
    pc_data["capital_service_cost"] = infrastructure_cost.capital_service_cost_2015

    pc = ProjectContent(**pc_data)

    db.session.add(pc)
    db.session.commit()

    return pc


for cluster_id, area in enumerate(areas):
    start_year_planning = parameter.START_YEAR - parameter.DURATION_PLANNING  # TODO: get start_year_planning and start_year of operation united
    start_year = parameter.START_YEAR
    duration_operation = parameter.DURATION_OPERATION

    # electrification
    traction = 'electrification'
    train_cost_electrification = calc_train_cost(traction=traction, area=area)
    infrastructure_cost(traction=traction, area=area, name=f"Complete electrification s{scenario_id}-a{area.id}", overwrite=True)
    logging.info(f"finished calculation electrification {cluster_id}")

    # efuel
    traction = 'efuel'
    train_cost_efuel = calc_train_cost(traction=traction, area=area)
    # at the moment there are no infrastructure cost for efuel
    logging.info(f"finished calculation efuel {cluster_id}")

    # h2
