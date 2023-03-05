import jinja2
from jinja2 import Template
import os
from prosd.models import MasterScenario
from plot_map import plot_map

SCENARIO_ID = 4
template_file = 'report_template.tex'
export_file_path = f'../../../example_data/report_scenarios/s_{SCENARIO_ID}/'
filepath_images = export_file_path + 'files/'


def create_file():
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

    if not os.path.exists(export_file_path):
        os.makedirs(export_file_path)
        os.makedirs(filepath_images)

    export_file_md = export_file_path + f's_{SCENARIO_ID}.tex'

    template = latex_jinja_env.get_template(template_file)
    rendered_file = template.render(data)

    with open(export_file_md, 'w') as file:
        file.write(rendered_file)


scenario = MasterScenario.query.get(SCENARIO_ID)
main_areas = scenario.main_areas
count_master_area = len(main_areas)
length_areas = [area.length/1000 for area in main_areas]
length_scenario = sum(length_areas)
parameters = scenario.parameters
cost_effective_traction = parameters["cost_effective_traction"]

plot_map(
    scenario_id=scenario.id,
    filepath_image_directory=filepath_images,
    areas=main_areas
)
filepath_map = f'../report_scenarios/s_{scenario.id}/files/deutschland_map.png'

data = {
    "scenario_name": scenario.name,
    "scenario_id": scenario.id,
    "count_master_area": count_master_area,
    "length_scenario": length_scenario,
    "cost_effective_traction": cost_effective_traction,
    "cost_effective_traction_no_optimised": parameters["cost_effective_traction_no_optimised"],
    "filepath_d_map": filepath_map
}

create_file()