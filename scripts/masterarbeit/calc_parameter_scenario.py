from prosd.models import MasterScenario

scenario_id = 20

if __name__ == '__main__':
    scenario = MasterScenario.query.get(scenario_id)
    scenario.save_parameters()
