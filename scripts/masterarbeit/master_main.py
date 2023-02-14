import logging
import sqlalchemy
import networkx

from prosd import db, parameter
from prosd.models import ProjectContent, MasterArea, RouteTraingroup, TimetableTrainCost, MasterScenario, TimetableTrainGroup
from prosd.calculation_methods import use, cost, base
from prosd.manage_db.version import Version
from prosd.graph import railgraph, routing

logging.basicConfig(encoding='utf-8', level=logging.DEBUG)

base = base.BaseCalculation()
ROUTE_TRAINGROUP = False
DELETE_AREAS = False
CREATE_AREAS = False
OVERWRITE_INFRASTRUCTURE = True
scenario_id = 1
start_year_planning = parameter.START_YEAR - parameter.DURATION_PLANNING  # TODO: get start_year_planning and start_year of operation united
start_year = parameter.START_YEAR
duration_operation = parameter.DURATION_OPERATION


def calculate_cost_area(area, tractions, scenario_infra):
        for traction in tractions:
            if 'sgv' in area.categories and (traction == 'battery' or traction == 'h2'):
                continue
            else:
                logging.debug(f"started calculation {traction} {area.id}")
                area.calculate_infrastructure_cost(traction=traction, infra_version=scenario_infra, overwrite=OVERWRITE_INFRASTRUCTURE)
                area.calc_train_cost(traction=traction, infra_version=scenario_infra)
                logging.debug(f"finished calculation {traction} {area.id}")


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

    areas = MasterArea.query.filter(MasterArea.scenario_id == scenario.id).all()

    for cluster_id, area in enumerate(areas):
        logging.info(f"calculation {area} is started")
        calculate_cost_area(area, tractions, scenario_infra)
        logging.info(f"calculation {area} is finished")


if __name__ == '__main__':
    main(scenario_id=scenario_id)
