from tests.base import BaseTestCase
from prosd import parameter
from prosd.manage_db.version import Version
from prosd.models import MasterScenario, MasterArea, TimetableLine
from prosd.calculation_methods.cost import BvwpProjectBattery, BvwpProjectOptimisedElectrification, BvwpH2InfrastructureCost

tt_id = 1720
area_id = 12338
scenario_id = 40


def get_infra_version():
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    return scenario_infra


class TestCostBattery(BaseTestCase):
    def test_cost_battery(self):
        """
        Test the calculation cost of battery, testcase 1
        :return:
        """
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        infrastructure_cost = BvwpProjectBattery(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(infrastructure_cost.cost_2015 >= 0)


class TestOptimisedElectrification(BaseTestCase):
    def test_cost_optimised_electrification_area(self):
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        project_optimised_electrification = BvwpProjectOptimisedElectrification(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )


class TestInfrastructureCostH2(BaseTestCase):
    def test_infrastrcture_cost_h2_area(self):
        area_id = 267
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        project_h2 = BvwpH2InfrastructureCost(
            start_year_planning=parameter.START_YEAR,
            area=area,
            infra_version=infra_version
        )

        self.assertTrue(project_h2.cost_2015 > 0)