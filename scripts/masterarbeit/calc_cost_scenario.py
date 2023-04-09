import logging
from datetime import datetime

from prosd.models import MasterScenario
from prosd.manage_db.version import Version

scenario_id = 4
filepath_logging = f"../../example_data/master_logs/calc_scenario/s-{scenario_id}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
logging.basicConfig(filename=filepath_logging, encoding='utf-8', level=logging.INFO)


def main(scenario_id):
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    scenario.calc_cost_all_tractions(scenario_infra)
    for area in scenario.main_areas:
        area.save_parameters()
    scenario.save_parameters()

if __name__ == '__main__':
    main(scenario_id=scenario_id)
