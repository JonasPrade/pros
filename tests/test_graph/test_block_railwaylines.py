from tests.base import BaseTestCase
from prosd.graph.block_rw_lines import BlockRailwayLines


scenario_id = 100


class TestBlockRailwayLines(BaseTestCase):
    def test_create_project(self):
        from_ocp = 'HGA'
        to_ocp = 'HBEM'
        stations_via = []
        additional_ignore_ocp = ["HGA", "HBN", "HB", "HVAH", "HHAT", "HBEM", "HHMG", "HWUE", "HHUD", "HBH", "HHOY", "HD"]
        reroute_train_categories = ['sgv']
        project_content_name = "Sperrung Bremen – Osnabrück "
        following_ocps = {
        }

        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id)
        block_rw_lines.create_blocking_project(
            from_ocp=from_ocp,
            to_ocp=to_ocp,
            project_content_name=project_content_name,
            stations_via=stations_via,
            additional_ignore_ocp=additional_ignore_ocp,
            reroute_train_categories=reroute_train_categories,
            following_ocps=following_ocps
        )

    def test_route_traingroups_of_blocked_railwaylines(self):
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id)
        block_rw_lines.reroute_traingroups()

    def test_reroute_traingroups_without_blocked_lines(self):
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id)
        block_rw_lines.reroute_traingroups_without_blocked_lines()

    def test_delete_blocking_project(self):
        pc_id = 52790
        block_rw_lines = BlockRailwayLines(scenario_id=scenario_id)
        block_rw_lines.delete_blocking_project(pc_id=pc_id)

