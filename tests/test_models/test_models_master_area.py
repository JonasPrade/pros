from tests.base import BaseTestCase

from prosd.models import MasterArea, MasterScenario
from prosd.manage_db.version import Version

area_id = 120
scenario_id = 1


def get_infra_version():
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    return scenario_infra


class TestMasterAreaSubAreas(BaseTestCase):
    def test_create_subareas(self):
        area = MasterArea.query.get(area_id)
        area.create_sub_areas()
        count_sub_areas = len(area.sub_master_areas)
        self.assertTrue(count_sub_areas > 0)

    def test_delete_sub_areas(self):
        area = MasterArea.query.get(area_id)
        area.create_sub_areas()
        area.delete_sub_areas()
        self.assertTrue(len(area.sub_master_areas) == 0)


class TestMasterAreaTractionCost(BaseTestCase):
    def test_calc_traction_cost_electrification(self):
        """
        Test the train cost calculation
        :return:
        """
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        area.calc_train_cost(
            traction='electrification',
            infra_version=infra_version,
        )

    def test_calc_traction_cost_efuel(self):
        """
        Test the train cost calculation
        :return:
        """
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        area.calc_train_cost(
            traction='efuel',
            infra_version=infra_version,
        )

    def test_calc_traction_cost_battery(self):
        """
        Test the train cost calculation
        :return:
        """
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        area.calc_train_cost(
            traction='battery',
            infra_version=infra_version,
        )

    def test_calc_traction_cost_optimised_electrification(self):
        """
        Test the traction cost for optimised electrification
        :return:
        """
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        area.calc_train_cost(
            traction='optimised_electrification',
            infra_version=infra_version,
        )

    def test_calc_traction_cost_diesel(self):
        """
        Test the traction cost for diesel
        :return:
        """
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)

        ttc = area.calc_train_cost(
            traction='diesel',
            infra_version=infra_version,
        )

        self.assertTrue(ttc[0].cost > 0)

class TestMasterAreaInfrastructureCost(BaseTestCase):
    def test_calculate_infrastructure_cost_electrification(self):
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)
        traction = 'electrification'

        infrastructure_cost = area.calculate_infrastructure_cost(
            traction=traction,
            infra_version=infra_version,
            overwrite=True
        )

        self.assertTrue(round(infrastructure_cost.planned_total_cost) >= 0)

    def test_calculate_infrastructure_cost_efuel(self):
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)
        traction = 'efuel'

        infrastructure_cost = area.calculate_infrastructure_cost(
            traction=traction,
            infra_version=infra_version,
            overwrite=True
        )

        self.assertTrue(infrastructure_cost is None)

    def test_calculate_infrastructure_cost_battery(self):
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)
        traction = 'battery'

        infrastructure_cost = area.calculate_infrastructure_cost(
            traction=traction,
            infra_version=infra_version,
            overwrite=True
        )

        self.assertTrue(round(infrastructure_cost.planned_total_cost) >= 0)

    def test_calculate_infrastructure_cost_optimised_electrification(self):
        infra_version = get_infra_version()
        area = MasterArea.query.get(area_id)
        traction = 'optimised_electrification'

        infrastructure_cost = area.calculate_infrastructure_cost(
            traction=traction,
            infra_version=infra_version,
            overwrite=True
        )

        self.assertTrue(round(infrastructure_cost.planned_total_cost) >= 0)

