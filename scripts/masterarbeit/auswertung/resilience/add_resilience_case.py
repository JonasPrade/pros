from prosd.graph.block_rw_lines import BlockRailwayLines

scenario_id = 100
reference_scenario_id = 1

block_rw = BlockRailwayLines(
    scenario_id=scenario_id,
    reference_scenario_id=reference_scenario_id
)

from_ocp = 'RSD'
to_ocp = 'SKL'
stations_via = ["RNBO", "SKL", "SHO"]
additional_ignore_ocp = ["RLSM", "RL", "RLUM", "RLUR", "RLI", "RSD", "SKL", "SHO"]
reroute_train_categories = ['sgv']
project_content_name = "Sperrung Ludwigshafen – Neunkirchen"
following_ocps = {
    "RM": ["FWOR", "FMWG", "FGAL", "SNBR"]
}

pc = block_rw.create_blocking_project(
    from_ocp=from_ocp,
    to_ocp=to_ocp,
    project_content_name=project_content_name,
    stations_via=stations_via,
    additional_ignore_ocp=additional_ignore_ocp,
    reroute_train_categories=reroute_train_categories,
    following_ocps=following_ocps
)

print(pc.id)

