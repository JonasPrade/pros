import logging
import time
from datetime import datetime

from prosd import db, parameter
from prosd.models import ProjectContent, MasterArea, RouteTraingroup, TimetableTrainCost, MasterScenario, TimetableTrainGroup
from prosd.calculation_methods import use, cost, base
from prosd.manage_db.version import Version
from prosd.graph import railgraph, routing

filepath_logging = f"../../example_data/master_logs/{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
logging.basicConfig(filename=filepath_logging, encoding='utf-8', level=logging.ERROR)

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
                area.calculate_infrastructure_cost(traction=traction, infra_version=scenario_infra, overwrite=OVERWRITE_INFRASTRUCTURE)
                area.calc_train_cost(traction=traction, infra_version=scenario_infra)
                end_time = time.time()
                logging.info(f"finished calculation {traction} {area.id} (duration {end_time - start_time}s)")


def main(scenario_id):
    tractions = parameter.TRACTIONS

    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    if ROUTE_TRAINGROUP:
        scenario.route_traingroups(infra_version=scenario_infra)
    if DELETE_AREAS:
        scenario.delete_areas()
    if CREATE_AREAS:
        scenario.create_areas(infra_version=scenario_infra)

    areas = MasterArea.query.filter(
        MasterArea.scenario_id == scenario.id,
        MasterArea.superior_master_area == None
    ).all()

    for cluster_id, area in enumerate(areas):
        logging.info(f"calculation {area} is started")
        calculate_cost_area(area, tractions, scenario_infra)


if __name__ == '__main__':
    main(scenario_id=scenario_id)
