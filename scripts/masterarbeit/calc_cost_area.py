import logging
import time

from prosd import db, parameter
from prosd.models import ProjectContent, MasterArea, RouteTraingroup, TimetableTrainCost, MasterScenario, TimetableTrainGroup
from prosd.calculation_methods import use, cost, base
from prosd.manage_db.version import Version
from prosd.graph import railgraph, routing

logging.basicConfig(encoding='utf-8', level=logging.INFO)

if __name__ == '__main__':
    scenario_id = 4
    master_area_id = 3261

    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    area = MasterArea.query.get(master_area_id)
    area.calculate_cost(infra_version=scenario_infra, overwrite_infrastructure=parameter.OVERWRITE_INFRASTRUCTURE)
