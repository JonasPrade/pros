from prosd.graph.block_rw_lines import BlockRailwayLines

scenario_id = 100
reference_scenario_id = 1

block_rw = BlockRailwayLines(
    scenario_id=scenario_id,
    reference_scenario_id=reference_scenario_id
)

pc_id = 91762
block_rw_lines = BlockRailwayLines(scenario_id=scenario_id, reference_scenario_id=reference_scenario_id)
block_rw_lines.delete_blocking_project(pc_id=pc_id)
