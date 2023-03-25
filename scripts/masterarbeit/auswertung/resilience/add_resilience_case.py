from prosd.graph.block_rw_lines import BlockRailwayLines

scenario_id = 100
reference_scenario_id = 1

block_rw = BlockRailwayLines(
    scenario_id=scenario_id,
    reference_scenario_id=reference_scenario_id
)

from_ocp = "MLEF"
to_ocp = "MBU"
stations_via = []
additional_ignore_ocp = ["MPGO", "MPG", "MP", "MLEF"]
reroute_train_categories = ['sgv', 'spfv']
project_content_name = "Sperrung München – Buchloe"
following_ocps = {

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

