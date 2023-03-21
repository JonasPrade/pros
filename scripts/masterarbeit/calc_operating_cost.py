from prosd.models import TimetableTrainCost, TimetableTrainGroup, MasterScenario
from prosd.manage_db.version import Version

if __name__ == '__main__':
    tractions = ['efuel']
    for traction in tractions:
        scenario_id = 21
        scenario = MasterScenario.query.get(scenario_id)
        scenario_infra = Version(scenario=scenario)
        scenario.calc_operating_cost_one_traction(traction=traction, infra_version=scenario_infra, overwrite_operating_cost = True)
