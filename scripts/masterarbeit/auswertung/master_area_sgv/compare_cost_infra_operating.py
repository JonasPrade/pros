from prosd.models import MasterArea, TimetableTrainGroup, TimetableTrain, TimetableTrainPart, TimetableCategory, traingroups_to_masterareas, MasterScenario
import pandas

scenario_id = 1
filepath = f'../../../../example_data/report_scenarios/s_{scenario_id}/proportion_operating_to_infrastructure_cost.tex'
scenario = MasterScenario.query.get(scenario_id)
categories = ['sgv']
areas = MasterArea.query.join(traingroups_to_masterareas).join(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).filter(
        MasterArea.scenario_id == scenario.id,
        MasterArea.superior_master_id == None,
        TimetableCategory.transport_mode.in_(categories)
    ).all()

area_numbers = {area.id:index for index, area in enumerate(areas)}

prioritization= {}
for area in areas:
    prioritization[area_numbers[area.id]] = {}
    prioritization[area_numbers[area.id]]["area_number"] = area_numbers[area.id]
    prioritization[area_numbers[area.id]]["operating_cost"] = area.operating_cost_all_tractions[area.cost_effective_traction]
    prioritization[area_numbers[area.id]]["infrastructure_cost"] = area.infrastructure_cost_all_tractions[area.cost_effective_traction]
    prioritization[area_numbers[area.id]]["proportion"] = area.infrastructure_cost_all_tractions[area.cost_effective_traction]/area.operating_cost_all_tractions[area.cost_effective_traction]

df = pandas.DataFrame.from_dict(prioritization)
df.to_latex(filepath, index=False)
