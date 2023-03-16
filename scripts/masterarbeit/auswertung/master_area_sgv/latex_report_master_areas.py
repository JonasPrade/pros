import jinja2
import os

from prosd.models import MasterScenario, MasterArea, TimetableTrain, TimetableTrainGroup, TimetableTrainPart, TimetableCategory, traingroups_to_masterareas
from prosd.manage_db.version import Version
from plot_maps_report_master_areas import plot_areas
from prosd import parameter

SCENARIO_ID = 4
export_file_path = f'../../../../example_data/report_scenarios/s_{SCENARIO_ID}/'
filepath_images = export_file_path + 'files/'
categories = ['sgv']


def create_file(data):
    template_file = 'areas_template.tex'
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
    export_file_md = export_file_path + f's_{SCENARIO_ID}_master_areas.tex'

    template = latex_jinja_env.get_template(template_file)
    rendered_file = template.render(data)

    with open(export_file_md, 'w') as file:
        file.write(rendered_file)


if __name__ == '__main__':
    scenario = MasterScenario.query.get(SCENARIO_ID)
    infra_version = Version(scenario=scenario)
    areas = MasterArea.query.join(traingroups_to_masterareas).join(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
        MasterArea.scenario_id == scenario.id,
        MasterArea.superior_master_id == None,
        TimetableCategory.transport_mode.in_(categories)
    ).all()

    area_numbers = {area.id:index for index, area in enumerate(areas)}

    filepath_map_areas = f'../report_scenarios/s_{scenario.id}/files/master_areas_sgv'

    # plot_areas(
    #     areas=areas,
    #     filepath_image_directory=filepath_images,
    #     scenario_name=scenario.name,
    #     area_numbers=area_numbers
    # )

    data = {
        "scenario": scenario,
        "transport_modes": categories,
        "filepath_master_areas_sgv": filepath_map_areas,
        "areas": areas,
        "area_numbers": area_numbers,
        "tractions": parameter.TRACTIONS
    }

    create_file(data=data)

