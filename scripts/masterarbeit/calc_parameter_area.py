
from prosd.models import MasterScenario, MasterArea

scenario_id = 100

if __name__ == '__main__':
    scenario = MasterScenario.query.get(scenario_id)
    for area in scenario.master_areas:
        area.save_parameters()
