from tests.base import BaseTestCase
from prosd import parameter
from prosd.manage_db.version import Version
from prosd.models import MasterScenario, MasterArea
from prosd.calculation_methods.cost import BvwpProjectBattery


def calculate_battery():
    scenario_id = 1
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    return scenario_infra


class TestCostBattery(BaseTestCase):
    def test_cost_battery_testcase1(self):
        """
        Test the calculation cost of battery, testcase 1
        :return:
        """
        area_id = 73
        infra_version = calculate_battery()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 > 0)

    def test_cost_battery_testcase2(self):
        """
        Test the calculation cost of battery, testcase 1
        :return:
        """
        area_id = 81
        infra_version = calculate_battery()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 == 0)

    def test_cost_battery_testcase3(self):
        area_id = 148
        infra_version = calculate_battery()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 == 0)

    def test_cost_battery_testcase4(self):
        area_id = 76
        infra_version = calculate_battery()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 == 0)



