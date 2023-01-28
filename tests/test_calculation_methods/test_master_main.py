from tests.base import BaseTestCase

from prosd.manage_db.version import Version
from scripts.masterarbeit import master_main
from prosd.models import MasterScenario, MasterArea
from prosd import parameter

area_id = 73

def get_infra_version(scenario_id):
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    return scenario_infra


class TestMasterMain(BaseTestCase):

    def test_infrastructure_cost_electrification(self):
        scenario_id = 1
        infra_version = get_infra_version(scenario_id)
        area = MasterArea.query.get(area_id)
        traction='electrification'

        infrastructure_cost = master_main.infrastructure_cost(
            area=area,
            name=f"{traction} s{infra_version.scenario.id}-a{area.id}",
            traction=traction,
            infra_version=infra_version,
            overwrite=True
        )

        self.assertTrue(round(infrastructure_cost.planned_total_cost) >= 0)

    def test_infrastructure_cost_battery(self):
        scenario_id = 1
        infra_version = get_infra_version(scenario_id)
        area = MasterArea.query.get(area_id)
        traction='battery'

        pc = master_main.infrastructure_cost(
            area=area,
            name=f"{traction} s{infra_version.scenario.id}-a{area.id}",
            traction=traction,
            infra_version=infra_version,
            overwrite=True
        )

        self.assertTrue(round(pc.planned_total_cost) >= 0)


