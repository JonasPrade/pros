import jinja2
from jinja2 import Template
import os
from prosd.models import MasterScenario, TimetableTrainGroup, TimetableTrain, TimetableTrainPart, TimetableCategory, RouteTraingroup, RailwayLine
from plot_map_areas_traction import plot_map_traction, plot_map_traction_without_optimised_electrificaton
from prosd import db
from prosd.manage_db.version import Version
from sgv_no_catenary import running_km_no_catenary, running_km_all

SCENARIO_ID = 42
template_file = 'report_template.tex'
export_file_path = f'../../../example_data/report_scenarios/s_{SCENARIO_ID}/'
filepath_images = export_file_path + 'files/'
AUSGANGSZENARIO = True

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
    export_file_md = export_file_path + f's_{SCENARIO_ID}.tex'

    template = latex_jinja_env.get_template(template_file)
    rendered_file = template.render(data)

    with open(export_file_md, 'w') as file:
        file.write(rendered_file)


def sgv_parameters(infra_version, scenario_id):
    rw_lines_no_catenary = infra_version.get_railwayline_no_catenary()

    sgv_lines = db.session.query(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(
        TimetableCategory).join(RouteTraingroup).join(RailwayLine).filter(
        TimetableCategory.transport_mode == 'sgv',
        RouteTraingroup.master_scenario_id == scenario_id,
        RailwayLine.id.in_(rw_lines_no_catenary)
    ).group_by(TimetableTrainGroup.id).all()

    running_km = [sgv.running_km_day(scenario_id) for sgv in sgv_lines]
    sum_running_km = sum(running_km)

    return sum_running_km


if not os.path.exists(export_file_path):
    os.makedirs(export_file_path)
if not os.path.exists(filepath_images):
    os.makedirs(filepath_images)

scenario = MasterScenario.query.get(SCENARIO_ID)
infra_version = Version(scenario=scenario)
main_areas = scenario.main_areas
count_master_area = len(main_areas)
length_areas = [area.length/1000 for area in main_areas]
length_scenario = sum(length_areas)
parameters = scenario.parameters
cost_effective_traction = parameters["cost_effective_traction"]
sum_running_km_traingroups_no_catenary = sgv_parameters(infra_version=infra_version, scenario_id=scenario.id)

plot_map_traction(filepath_image_directory=filepath_images, areas=main_areas)
plot_map_traction_without_optimised_electrificaton(
    filepath_image_directory=filepath_images,
    areas=main_areas
)

filepath_map_tractions_latex = f'../report_scenarios/s_{scenario.id}/files/deutschland_map'
filepath_map_tractions_no_optimised_latex = f'../report_scenarios/s_{scenario.id}/files/traction_map_no_optimised'

parameter_ausgangszenario = {}

parameter_ausgangszenario["infra_km_sgv_all"], parameter_ausgangszenario["running_km_sgv_all"] = running_km_all(transport_modes = ['sgv'])
parameter_ausgangszenario["infra_km_sgv_no_catenary"], parameter_ausgangszenario["running_km_sgv_no_catenary"] = running_km_no_catenary(transport_modes = ['sgv'])
parameter_ausgangszenario["infra_relativ_sgv"] = round(parameter_ausgangszenario["infra_km_sgv_no_catenary"]/parameter_ausgangszenario["infra_km_sgv_all"]*100, 2)
parameter_ausgangszenario["running_relativ_sgv"] = round(parameter_ausgangszenario["running_km_sgv_no_catenary"]/parameter_ausgangszenario["running_km_sgv_all"]*100, 2)

parameter_ausgangszenario["infra_km_spfv_all"], parameter_ausgangszenario["running_km_spfv_all"] = running_km_all(transport_modes=['spfv'])
parameter_ausgangszenario["infra_km_spfv_no_catenary"], parameter_ausgangszenario["running_km_spfv_no_catenary"] = running_km_no_catenary(transport_modes=['spfv'])
parameter_ausgangszenario["infra_relativ_spfv"] = round(parameter_ausgangszenario["infra_km_spfv_no_catenary"]/parameter_ausgangszenario["infra_km_spfv_all"]*100, 2)
parameter_ausgangszenario["running_relativ_spfv"] = round(parameter_ausgangszenario["running_km_spfv_no_catenary"]/parameter_ausgangszenario["running_km_spfv_all"]*100, 2)

parameter_ausgangszenario["infra_km_spnv_all"], parameter_ausgangszenario["running_km_spnv_all"] = running_km_all(transport_modes=['spnv'])
parameter_ausgangszenario["infra_km_spnv_no_catenary"], parameter_ausgangszenario["running_km_spnv_no_catenary"]= running_km_no_catenary(transport_modes=['spnv'])
parameter_ausgangszenario["infra_relativ_spnv"] = round(parameter_ausgangszenario["infra_km_spnv_no_catenary"]/parameter_ausgangszenario["infra_km_spnv_all"]*100, 2)
parameter_ausgangszenario["running_relativ_spnv"] = round(parameter_ausgangszenario["running_km_spnv_no_catenary"]/parameter_ausgangszenario["running_km_spnv_all"]*100, 2)

parameter_ausgangszenario["infra_km_all"], parameter_ausgangszenario["running_km_all"] = running_km_all(transport_modes=['sgv', 'spfv', 'spnv'])
parameter_ausgangszenario["infra_km_all_no_catenary"], parameter_ausgangszenario["running_km_all_no_catenary"] = running_km_no_catenary(transport_modes=['sgv', 'spfv', 'spnv'])
parameter_ausgangszenario["infra_relativ_all"] = round(parameter_ausgangszenario["infra_km_all_no_catenary"]/parameter_ausgangszenario["infra_km_all"]*100, 2)
parameter_ausgangszenario["running_relativ_all"] = round(parameter_ausgangszenario["running_km_all_no_catenary"]/parameter_ausgangszenario["running_km_all"]*100, 2)


data = {
    "scenario_name": scenario.name,
    "scenario_id": scenario.id,
    "count_master_area": count_master_area,
    "length_scenario": length_scenario,
    "cost_effective_traction": cost_effective_traction,
    "cost_effective_traction_no_optimised": parameters["cost_effective_traction_no_optimised"],
    "filepath_d_map": filepath_map_tractions_latex,
    "sum_cost_infrastructure": parameters["sum_infrastructure"],
    "sum_cost_operating": parameters["sum_operating_cost"],
    "sum_running_km_traingroups_no_catenary": sum_running_km_traingroups_no_catenary,
    "co2_old": parameters["co2_old"],
    "co2_new": parameters["co2_new"],
    "print_parameter_ausgangszenario": AUSGANGSZENARIO,
    "parameter_ausgangszenario": parameter_ausgangszenario,
    "running_km_by_transport_mode_by_traction": parameters["running_km_by_transport_mode"]
}

create_file(data=data)
