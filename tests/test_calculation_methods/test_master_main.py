from tests.base import BaseTestCase

from prosd.manage_db.version import Version
from scripts.masterarbeit import master_main
from prosd.models import MasterScenario, MasterArea
from prosd import parameter


def get_infra_version(scenario_id):
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    return scenario_infra


class TestMasterMain(BaseTestCase):
    def test_cost_area_battery(self):
        """
        Test the cost caclculation for an area
        :return:
        """
        area_id = 60
        scenario_id = 1
        traction = ["battery"]
        area = MasterArea.query.get(area_id)
        scenario_infra = get_infra_version(scenario_id)
        master_main.calculate_cost_area(
            area=area,
            tractions=traction,
            scenario_infra=scenario_infra
        )

