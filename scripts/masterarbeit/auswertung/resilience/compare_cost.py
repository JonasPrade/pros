import json

from prosd.graph.block_rw_lines import BlockRailwayLines

scenario_id = 100
reference_scenario_id = 1
pc_id = 91843

block_rw = BlockRailwayLines(
    scenario_id=scenario_id,
    reference_scenario_id=reference_scenario_id
)


answ = block_rw.compare_cost_for_project(
    pc_id=pc_id
)

filepath_save_cost = f'../../../../example_data/railgraph/blocked_scenarios/s_100_results/{pc_id}_results.json'

with open(filepath_save_cost, 'w') as outfile:
    json.dump(answ, outfile)

