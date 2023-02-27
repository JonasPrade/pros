from prosd.models import TimetableTrainCost, TimetableTrainGroup, MasterScenario
from prosd.manage_db import version

traingroup_id = 'tg_BB26.b_N_x0020_26202_9862'
traction = 'h2'
scenario_id = 3
calculation_method = 'standi'

traingroup = TimetableTrainGroup.query.get(traingroup_id)
scenario = MasterScenario.query.get(scenario_id)
infra_version = version.Version(scenario)

TimetableTrainCost.create(
    traingroup = traingroup,
    master_scenario_id = scenario_id,
    traction = traction,
    infra_version=infra_version,
    calculation_method = calculation_method
)
