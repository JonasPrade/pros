from prosd.models import TimetableTrainCost, TimetableTrainGroup, MasterScenario
from prosd.manage_db.version import Version

if __name__ == '__main__':
    tractions = ['optimised_electrification']
    for traction in tractions:
        scenario_id = 42
        scenario = MasterScenario.query.get(scenario_id)
        scenario_infra = Version(scenario=scenario)
        scenario.calc_infrastructure_cost_one_traction(traction=traction, infra_version=scenario_infra, overwrite=True)
        for area in scenario.main_areas:
            area.save_parameters()
        scenario.save_parameters()