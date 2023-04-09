import logging
from datetime import datetime

from prosd import parameter
from prosd.manage_db.version import Version
from prosd.models import MasterArea, MasterScenario

scenario_id = 4
master_area_id = 4853

filepath_logging = f"../../example_data/master_logs/calc_area/a-{master_area_id}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
logging.basicConfig(filename=filepath_logging, encoding='utf-8', level=logging.INFO)

if __name__ == '__main__':
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    area = MasterArea.query.get(master_area_id)
    area.calculate_cost(infra_version=scenario_infra, overwrite_infrastructure=parameter.OVERWRITE_INFRASTRUCTURE)
