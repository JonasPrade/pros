from tests.base import BaseTestCase

from prosd.models import MasterArea, MasterScenario
from prosd.manage_db.version import Version

scenario_id = 1


def get_infra_version():
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    return scenario_infra


class TestMasterScenario(BaseTestCase):
    def test_create_areas(self):
        scenario = MasterScenario.query.get(scenario_id)
        infra_version = get_infra_version()
        scenario.delete_areas()
        scenario.create_areas(infra_version)

    def test_delete_areas(self):
        scenario = MasterScenario.query.get(scenario_id)
        scenario.delete_areas()

    def test_cost_effective_traction(self):
        scenario = MasterScenario.query.get(scenario_id)
        cost_effective_traction = scenario.cost_effective_traction
        self.assertTrue(len(cost_effective_traction) > 0)

    def test_parameters(self):
        scenario = MasterScenario.query.get(scenario_id)
        parameters = scenario.parameters
        self.assertTrue(len(parameters) > 0)
