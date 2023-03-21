from tests.base import BaseTestCase
from prosd.graph.block_rw_lines import BlockRailwayLines
from prosd.models import TimetableTrainGroup


scenario_id = 100
reference_scenario_id = 4
traingroup_id = "tg_677_x0020_G_x0020_2501_112538"


class TestBlockRailwayLines(BaseTestCase):
    def test_create_project(self):
        from_ocp = 'RSD'
        to_ocp = 'SKL'
        stations_via = ["RNBO", "SKL", "SHO"]
        additional_ignore_ocp = ["RLSM", "RL", "RLUM", "RLUR", "RLI", "RSD", "SKL", "SHO"]
        reroute_train_categories = ['sgv']
        project_content_name = "Sperrung Ludwigshafen – Neunkirchen"
        following_ocps = {
            "RM": ["FWOR", "FMWG", "FGAL", "SNBR"]
        }

        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
        block_rw_lines.create_blocking_project(
            from_ocp=from_ocp,
            to_ocp=to_ocp,
            project_content_name=project_content_name,
            stations_via=stations_via,
            additional_ignore_ocp=additional_ignore_ocp,
            reroute_train_categories=reroute_train_categories,
            following_ocps=following_ocps
        )

    def test_compare_cost_for_project(self):
        pc_id = 55498
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
        costs = block_rw_lines.compare_cost_for_project(pc_id)

    def test_route_traingroups_of_blocked_railwaylines(self):
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
        block_rw_lines.reroute_traingroups()

    def test_reroute_traingroups_without_blocked_lines(self):
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
        block_rw_lines.reroute_traingroups_without_blocked_lines()

    def test_delete_blocking_project(self):
        pc_id = 72637
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
        block_rw_lines.delete_blocking_project(pc_id=pc_id)

    def test_get_areas_for_tg(self):
        tg = TimetableTrainGroup.query.get(traingroup_id)
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
        areas = block_rw_lines.get_areas_for_tg(tg)