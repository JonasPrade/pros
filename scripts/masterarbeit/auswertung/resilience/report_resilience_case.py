import os
import jinja2
import json

from prosd.models import ProjectContent, TimetableTrainGroup, MasterArea, MasterScenario
from plot_resilience_map import plot_resilience_map
from prosd.graph.block_rw_lines import BlockRailwayLines
from prosd import parameter
from prosd.manage_db.version import Version

scenario_id = 100
reference_scenario_id = 1
pc_ids = [92902]


for pc_id in pc_ids:
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
        scenario = MasterScenario.query.get(scenario_id)
        infra_version = Version(scenario=scenario)

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

        count_trains = sum([len(tg.trains) for tg in tgs])
        running_km_day_reference_scenario = sum([tg.running_km_day(reference_scenario_id) for tg in tgs])
        running_km_day_resilience_scenario = sum([tg.running_km_day(scenario_id) for tg in tgs])
        rw_lines_ref_scenario = set()
        rw_lines_res_scenario = set()
        for tg in tgs:
            rw_lines_ref_scenario.update(element for element in tg.railway_lines_scenario(reference_scenario_id))
            rw_lines_res_scenario.update(element for element in tg.railway_lines_scenario(scenario_id))

        new_rw_lines = rw_lines_res_scenario - rw_lines_ref_scenario
        new_rw_lines_not_electrified = set()
        for line in new_rw_lines:
            line_model = infra_version.get_railwayline_model(railwayline_id=line.id)
            if line_model.catenary is False:
                new_rw_lines_not_electrified.add(line)
        length_rw_lines_not_electrified = sum([line.length/1000 for line in new_rw_lines_not_electrified])

        with open(filepath_save_cost, 'r') as openfile:
            cost = json.load(openfile)

        plot_resilience_map(
            pc=pc,
            additional_info=additional_info,
            filepath_dir=filepath_resilience_case,
            tgs=tgs,
            scenario_id=scenario_id
        )

        if cost["cost_resilience"] < cost["cost_road_case"]:
            preferred_scenario = "Umleitung Schiene"
        else:
            preferred_scenario = "Straße"

        filepath_map = f'../report_scenarios/resilience_cases/{pc_id}/resilience_map_{pc_id}.png'
        data = dict()
        data["pc"] = pc
        data["additional_data"] = additional_info
        data["cost"] = cost
        data["filepath_map"] = filepath_map
        data["count_trains"] = count_trains
        data["running_km_day_reference_scenario"] = running_km_day_reference_scenario
        data["running_km_day_resilience_scenario"] = running_km_day_resilience_scenario
        data["parameter"] = parameter
        data["preferred_scenario"] = preferred_scenario
        data["rw_lines_ref_scenario"] = rw_lines_ref_scenario
        data["rw_lines_res_scenario"] = rw_lines_res_scenario
        data["length_new_rw_lines"] = length_rw_lines_not_electrified

        create_file(data=data)
