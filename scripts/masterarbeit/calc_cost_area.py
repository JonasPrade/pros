import logging
import time

from prosd import db, parameter
from prosd.models import ProjectContent, MasterArea, RouteTraingroup, TimetableTrainCost, MasterScenario, TimetableTrainGroup
from prosd.calculation_methods import use, cost, base
from prosd.manage_db.version import Version
from prosd.graph import railgraph, routing

logging.basicConfig(encoding='utf-8', level=logging.INFO)

base = base.BaseCalculation()
ROUTE_TRAINGROUP = False
DELETE_AREAS = False
CREATE_AREAS = False
OVERWRITE_INFRASTRUCTURE = True
scenario_id = 2
start_year_planning = parameter.START_YEAR - parameter.DURATION_PLANNING  # TODO: get start_year_planning and start_year of operation united
start_year = parameter.START_YEAR
duration_operation = parameter.DURATION_OPERATION


def calculate_cost_area(area, tractions, scenario_infra):
    for traction in tractions:
        if 'sgv' in area.categories and (traction == 'battery' or traction == 'h2'):
            continue
        else:
            start_time = time.time()
            area.calculate_infrastructure_cost(traction=traction, infra_version=scenario_infra,
                                               overwrite=OVERWRITE_INFRASTRUCTURE)
            area.calc_train_cost(traction=traction, infra_version=scenario_infra)
            end_time = time.time()
            logging.info(f"finished calculation {traction} {area.id} (duration {end_time - start_time}s)")


if __name__ == '__main__':
    master_area_id = 337
    tractions = parameter.TRACTIONS

    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    if ROUTE_TRAINGROUP:
        scenario.route_traingroups(infra_version=scenario_infra)
    if DELETE_AREAS:
        scenario.delete_areas()
    if CREATE_AREAS:
        scenario.create_areas(infra_version=scenario_infra)

    area = MasterArea.query.get(master_area_id)
    calculate_cost_area(area, tractions, scenario_infra)
