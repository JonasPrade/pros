import logging

from prosd.models import MasterScenario

from prosd.manage_db.version import Version

scenario_id = 4
traction = 'electrification'
filepath_logging = f"../../example_data/master_logs/calc_traction/s-{scenario_id}_traction-{traction}.log"
logging.basicConfig(filename=filepath_logging, encoding='utf-8', level=logging.INFO, filemode='w')


if __name__ == '__main__':
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    scenario.calc_cost_one_traction(traction=traction, infra_version=scenario_infra)
