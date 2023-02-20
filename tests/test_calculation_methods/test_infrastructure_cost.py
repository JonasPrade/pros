from tests.base import BaseTestCase
from prosd import parameter
from prosd.manage_db.version import Version
from prosd.models import MasterScenario, MasterArea, TimetableLine
from prosd.calculation_methods.cost import BvwpProjectBattery, BvwpProjectOptimisedElectrification

tt_id = 1720

def get_infra_version():
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
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 >= 0)

    def test_cost_battery_testcase2(self):
        """
        Test the calculation cost of battery, testcase 1
        :return:
        """
        area_id = 81
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 == 0)

    def test_cost_battery_testcase3(self):
        area_id = 148
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 == 0)

    def test_cost_battery_testcase4(self):
        area_id = 76
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 == 0)

    def test_cost_battery_testcase_area64(self):
        area_id = 64
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(round(infrastructure_cost.cost_2015) == 16296)

    def test_cost_battery_testcase_area73(self):
        area_id = 73
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(round(infrastructure_cost.cost_2015) == 0)

    def test_cost_battery_testcase_area74(self):
        area_id = 74
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(round(infrastructure_cost.cost_2015) == 48888)

    def test_cost_battery_testcase_area251(self):
        area_id = 251
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(round(infrastructure_cost.cost_2015) > 0)


class TestOptimisedElectrification(BaseTestCase):
    def test_cost_optimised_electrification_area_60(self):
        area_id = 60
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        project_optimised_electrification = BvwpProjectOptimisedElectrification(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

    def test_cost_optimised_electrification_area_58(self):
        area_id = 58
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        project_optimised_electrification = BvwpProjectOptimisedElectrification(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

    def test_cost_optimised_electrification_area_106(self):
        area_id = 106
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        project_optimised_electrification = BvwpProjectOptimisedElectrification(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

    def test_cost_optimised_electrification_area(self):
        area_id = 266
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        project_optimised_electrification = BvwpProjectOptimisedElectrification(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(project_optimised_electrification.planned_total_cost > 0)
