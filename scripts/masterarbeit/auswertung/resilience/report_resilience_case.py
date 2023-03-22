import os
import jinja2
import json

from prosd.models import ProjectContent, TimetableTrainGroup
from plot_resilience_map import plot_resilience_map
from prosd.graph.block_rw_lines import BlockRailwayLines

scenario_id = 100
reference_scenario_id = 1
pc_id = 91762
template_file = 'template_resilience_case.tex'
filepath_resilience_case = f'../../../../example_data/report_scenarios/resilience_cases/{pc_id}/'
filepath_tex = filepath_resilience_case+f'resilience_case_{pc_id}.tex'
filepath_save_cost = f'../../../../example_data/railgraph/blocked_scenarios/s_100_results/{pc_id}_results.json'


def create_file(data):
    latex_jinja_env = jinja2.Environment(
        block_start_string='\BLOCK{',
        block_end_string='}',
        variable_start_string='\VAR{',
        variable_end_string='}',
        comment_start_string='\#{',
        comment_end_string='}',
        line_statement_prefix='%%',
        line_comment_prefix='%#',
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(os.path.abspath('.'))
    )
    export_file_latex = filepath_tex

    template = latex_jinja_env.get_template(template_file)
    rendered_file = template.render(data)

    with open(export_file_latex, 'w') as file:
        file.write(rendered_file)


if __name__ == '__main__':
    block_rw = BlockRailwayLines(
        scenario_id=scenario_id,
        reference_scenario_id=reference_scenario_id
    )

    if not os.path.exists(filepath_resilience_case):
        os.makedirs(filepath_resilience_case)

    pc = ProjectContent.query.get(pc_id)
    additional_info = block_rw._read_additional_project_info()[str(pc_id)]
    tgs = [TimetableTrainGroup.query.get(tg) for tg in additional_info["traingroups_to_reroute"]]
    block_rw._reroute_traingroup(
        pc=pc,
        tgs=tgs,
        additional_data=additional_info
    )
    with open(filepath_save_cost, 'r') as openfile:
        cost = json.load(openfile)

    plot_resilience_map(
        pc=pc,
        additional_info=additional_info,
        filepath_dir=filepath_resilience_case,
        tgs = tgs,
        scenario_id = scenario_id
    )

    data = dict()
    data["pc"] = pc
    data["cost"] = cost

    create_file(data=data)
