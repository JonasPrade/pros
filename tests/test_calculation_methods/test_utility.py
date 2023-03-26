from tests.base import BaseTestCase

from prosd.models import TimetableTrainGroup, MasterScenario, RouteTraingroup, RailwayLine, TimetableTrainCost, TimetableLine
from prosd import parameter
from prosd.calculation_methods import use
from prosd.manage_db.version import Version

def preparation():
    start_year = parameter.START_YEAR
    duration_operation = parameter.DURATION_OPERATION

    scenario_id = 1
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    return start_year, duration_operation, scenario_infra


class TestCostSgv(BaseTestCase):
    def test_cost_electrification_sgv(self):
        start_year, duration_operation, scenario_infra = preparation()

        traingroup_id = 'tg_323_x0020_G_x0020_4002_122463'
        traingroup = TimetableTrainGroup.query.get(traingroup_id)
        print(traingroup.category.transport_mode)

        cost = use.BvwpSgv(
            tg=traingroup,
            traction='electrification',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year>0)

    def test_cost_efuel_sgv(self):
        start_year, duration_operation, scenario_infra = preparation()

        traingroup_id = 'tg_SH_AS_x0020_09903_132927'
        traingroup = TimetableTrainGroup.query.get(traingroup_id)
        print(traingroup.category.transport_mode)

        cost = use.BvwpSgv(
            tg=traingroup,
            traction='efuel',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_diesel_sgv(self):
        start_year, duration_operation, scenario_infra = preparation()

        traingroup_id = 'tg_SH_AS_x0020_09903_132927'
        traingroup = TimetableTrainGroup.query.get(traingroup_id)
        print(traingroup.category.transport_mode)

        cost = use.BvwpSgv(
            tg=traingroup,
            traction='diesel',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_electrification_spfv_bvwp(self):
        start_year, duration_operation, scenario_infra = preparation()

        traingroup_id = 'tg_FR5.a_x0020_H_x0020_5101_127537'
        traingroup = TimetableTrainGroup.query.get(traingroup_id)
        print(traingroup.category.transport_mode)

        cost = use.BvwpSpfv(
            tg=traingroup,
            traction='electrification',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    # def test_cost_diesel_spfv_bvwp(self):
    #     start_year, duration_operation, scenario_infra = preparation()
    #
    #     traingroup_id = 'tg_FR5.a_x0020_H_x0020_5101_127537'
    #     traingroup = TimetableTrainGroup.query.get(traingroup_id)
    #
    #     cost = use.BvwpSpfv(
    #         tg=traingroup,
    #         traction='diesel',
    #         start_year_operation=start_year,
    #         duration_operation=duration_operation,
    #         infra_version=scenario_infra
    #     )
    #     self.assertTrue(cost.use_base_year > 0)

    def test_cost_electrification_spfv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='electrification',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_efuel_spfv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='efuel',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_diesel_spfv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='diesel',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_battery_spfv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='battery',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_h2_spfv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='h2',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_electrification_spnv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '1247'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='electrification',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_efuel_spnv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='efuel',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_diesel_spnv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='diesel',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_h2_spnv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='h2',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)

    def test_cost_battery_spnv_standi(self):
        start_year, duration_operation, scenario_infra = preparation()

        trainline_id = '2364'
        trainline = TimetableLine.query.get(trainline_id)

        cost = use.StandiSpnv(
            trainline=trainline,
            traction='battery',
            start_year_operation=start_year,
            duration_operation=duration_operation,
            infra_version=scenario_infra
        )
        self.assertTrue(cost.use_base_year > 0)



