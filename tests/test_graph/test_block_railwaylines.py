from tests.base import BaseTestCase
from prosd.graph.block_rw_lines import BlockRailwayLines
from prosd.models import TimetableTrainGroup, ProjectContent
import os

scenario_id = 100
reference_scenario_id = 4
traingroup_id = "tg_677_x0020_G_x0020_2501_112538"


def create_block_rw_lines():
    block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
    block_rw_lines.filepath_block_template = f'../../example_data/railgraph/blocked_scenarios/s-{scenario_id}_test.json'
    dirname = os.path.dirname(__file__)
    block_rw_lines.filepath_block = os.path.realpath(os.path.join(dirname, block_rw_lines.filepath_block_template))
    return block_rw_lines


class TestBlockRailwayLines(BaseTestCase):
    def test_create_project(self):
        from_ocp = "MLEF"
        to_ocp = "MBU"
        stations_via = []
        additional_ignore_ocp = ["MPGO", "MPG", "MP", "MLEF"]
        reroute_train_categories = ['sgv', 'spfv']
        project_content_name = "Sperrung München – Buchloe"
        following_ocps = {

        }

        block_rw_lines = create_block_rw_lines()
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
        pc_id = 83774
        block_rw_lines = create_block_rw_lines()
        costs = block_rw_lines.compare_cost_for_project(pc_id)

    def test_reroute_traingroup_for_pc(self):
        pc_id = 92090
        block_rw_lines = create_block_rw_lines()

        pc = ProjectContent.query.get(pc_id)
        additional_data_all = block_rw_lines._read_additional_project_info()
        additional_data_pc = additional_data_all[str(pc_id)]
        traingroups = [TimetableTrainGroup.query.get(tg) for tg in additional_data_pc["traingroups_to_reroute"]]

        # route the traingroups
        block_rw_lines._reroute_traingroup(
            pc=pc,
            tgs=traingroups,
            additional_data=additional_data_pc
        )

    def test_route_traingroups_of_blocked_railwaylines(self):
        block_rw_lines = create_block_rw_lines()
        block_rw_lines.reroute_traingroups()

    def test_reroute_traingroups_without_blocked_lines(self):
        block_rw_lines = create_block_rw_lines()
        block_rw_lines.reroute_traingroups_without_blocked_lines()

    def test_delete_blocking_project(self):
        pc_id = 92089
        block_rw_lines = create_block_rw_lines()
        block_rw_lines.delete_blocking_project(pc_id=pc_id)

    def test_get_areas_for_tg(self):
        tg = TimetableTrainGroup.query.get(traingroup_id)
        block_rw_lines = create_block_rw_lines()
        areas = block_rw_lines.get_areas_for_tg(tg)