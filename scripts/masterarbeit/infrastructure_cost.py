from prosd.manage_db.version import Version
from prosd.models import MasterScenario, MasterArea
from prosd.calculation_methods import cost
from prosd import parameter

scenario_id = 2
scenario = MasterScenario.query.get(scenario_id)
scenario_infra = Version(scenario=scenario)
area = MasterArea.query.get(1)
railway_lines_scope = area.railway_lines

start_year_planning = parameter.START_YEAR

infrastructure_cost = cost.BvwpCostElectrification(
            railway_lines_scope=railway_lines_scope,
            start_year_planning=start_year_planning,
            abs_nbs='abs',
            infra_version=scenario_infra
        )

print(infrastructure_cost)
