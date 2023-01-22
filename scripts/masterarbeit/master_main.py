import logging
import sqlalchemy
import networkx

from prosd import db, parameter
from prosd.models import ProjectContent, MasterArea, RouteTraingroup, TimetableTrainCost, MasterScenario, TimetableTrainGroup
from prosd.calculation_methods import use, cost, base
from prosd.manage_db.version import Version
from prosd.graph import railgraph, routing

base = base.BaseCalculation()
OVERWRITE_INFRASTRUCTURE = True
ROUTE_TRAINGROUP = False
DELETE_AREAS = False
CREATE_AREAS = False
start_year_planning = parameter.START_YEAR - parameter.DURATION_PLANNING  # TODO: get start_year_planning and start_year of operation united
start_year = parameter.START_YEAR
duration_operation = parameter.DURATION_OPERATION


def calc_train_cost(traction, area, infra_version, scenario_id):
    trains_cost = dict()

    for tg in area.traingroups:
        ttc = TimetableTrainCost.query.filter(
            TimetableTrainCost.traingroup_id == tg.id,
            TimetableTrainCost.calculation_method == 'bvwp',
            TimetableTrainCost.master_scenario_id == scenario_id,
            TimetableTrainCost.traction == traction
        ).scalar()

        if ttc is None:
            ttc = TimetableTrainCost.query.filter(
                TimetableTrainCost.traingroup_id == tg.id,
                TimetableTrainCost.calculation_method == 'standi',
                TimetableTrainCost.master_scenario_id == scenario_id,
                TimetableTrainCost.traction == traction
            ).scalar()

        if ttc is None:
            try:
                ttc = TimetableTrainCost.create(
                    traingroup=tg,
                    master_scenario_id=scenario_id,
                    traction=traction,
                    infra_version=infra_version
                )
            except use.NoVehiclePatternExistsError as e:
                logging.error(e)
                continue

        trains_cost[tg.id] = base.cost_base_year(start_year=start_year, duration=duration_operation, cost=ttc.cost)

    return trains_cost


def infrastructure_cost(area, name, traction, infra_version, overwrite=True):
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
            railway_lines_scope=area.railway_lines,
            infra_version=infra_version
        )
    elif traction == "battery":
        infrastructure_cost = cost.BvwpProjectBattery(
            start_year_planning=start_year_planning,
            area=area,
            infra_version=infra_version
        )
    elif traction == 'efuel':
        return None
    elif traction == 'diesel':
        return None
    else:
        logging.error(f"no fitting traction found for {traction}")
        return None

    pc_data = dict()

    pc_data["name"] = name
    pc_data["master_areas"] = [area]
    # TODO: Add description

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

    if traction == 'electrification':
        pc_data["length"] = infrastructure_cost.length
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

    if traction == "battery":
        subprojects = infrastructure_cost.project_contents
        if subprojects:
            for project in subprojects:
                project.superior_project_content_id = pc.id
            db.session.add_all(subprojects)
            db.session.commit()

    return pc


def route_traingroups(infra_version):
    rg = railgraph.RailGraph()
    graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
    route = routing.GraphRoute(graph=graph, infra_version=infra_version)

    traingroups_route = db.session.query(TimetableTrainGroup).filter(
        ~sqlalchemy.exists().where(
            sqlalchemy.and_(
                RouteTraingroup.traingroup_id == TimetableTrainGroup.id,
                RouteTraingroup.master_scenario_id == infra_version.scenario.id
            )
        )
    ).all()

    for tg in traingroups_route:
        try:
            route.line(traingroup=tg, force_recalculation=False)
        except (UnboundLocalError, networkx.exception.NodeNotFound) as e:
            logging.error(f"{e.args} {tg}")


def calculate_cost_area(area, tractions, scenario_infra):
        for traction in tractions:
            if 'sgv' in area.categories and (traction == 'battery' or traction == 'h2'):
                continue
            else:
                calc_train_cost(traction=traction, area=area, infra_version=scenario_infra, scenario_id=scenario_infra.scenario.id)
                infrastructure_cost(traction=traction, area=area, name=f"{traction} s{scenario_infra.scenario.id}-a{area.id}",
                                    infra_version=scenario_infra, overwrite=OVERWRITE_INFRASTRUCTURE)
                logging.info(f"finished calculation {traction} {area.id}")


def main(scenario_id):
    tractions = parameter.TRACTIONS

    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    if ROUTE_TRAINGROUP:
        route_traingroups(infra_version=scenario_infra)
    if DELETE_AREAS:
        scenario.delete_areas()
    if CREATE_AREAS:
        scenario.create_areas(infra_version=scenario_infra)

    areas = MasterArea.query.filter(MasterArea.scenario_id == scenario.id).all()

    for cluster_id, area in enumerate(areas):
        calculate_cost_area(area, tractions, scenario_infra)


if __name__ == '__main__':

    scenario_id = 1
    main(scenario_id=scenario_id)
