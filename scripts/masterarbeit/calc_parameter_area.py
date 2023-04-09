
from prosd.models import MasterScenario, MasterArea

scenario_id = 21

if __name__ == '__main__':
    scenario = MasterScenario.query.get(scenario_id)
    for area in scenario.main_areas:
        area.save_parameters()
