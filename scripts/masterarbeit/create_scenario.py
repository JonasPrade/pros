from prosd.models import MasterScenario, ProjectContent, TimetableTrainCost, MasterArea, TractionOptimisedElectrification, RouteTraingroup
from prosd import db
import sqlalchemy

COPY_AREAS = 1  # set to scenario_id or if not needed to False
COPY_TRAIN_COST = 1 # set to scenario_id or if not needed to False
COPY_ROUTING = 1

scenario = MasterScenario(
    id = 21,
    name = 'e-Fuel günstiger (1€/l)',
    start_year = 2030,
    operation_duration = 30
)

project_content_ids = [
    18
]


def clone_model(model):
    table = model.__table__
    non_pk_columns = [k for k in table.columns.keys() if k not in table.primary_key]
    non_pk_columns.extend([k.key for k in model.__mapper__.relationships])
    data = {c: getattr(model, c) for c in non_pk_columns}
    return data


def copy_train_costs(copy_scenario_id, scenario):
    train_costs_copy_scenario = MasterScenario.query.get(copy_scenario_id).train_costs
    train_costs_to_scenario = []
    for cost in train_costs_copy_scenario:
        data = clone_model(cost)
        data["master_scenario_id"] = scenario.id
        data["master_scenario"] = scenario
        train_costs_to_scenario.append(TimetableTrainCost(**data))

    return train_costs_to_scenario


def copy_project_content(pcs, area):
    new_pcs = []
    for pc in pcs:
        pc_data = clone_model(pc)
        pc_data["master_areas"] = [area]
        new_pcs.append(ProjectContent(**pc_data))

    return new_pcs


def copy_sub_master_area(sub_master_areas, scenario, new_area):
    new_sub_master_areas = []
    for sub_area in sub_master_areas:
        data = clone_model(sub_area)
        data["scenario_id"] = scenario.id
        data["scenario"] = scenario
        data["superior_master_id"] = new_area.id
        data["superior_master_area"] = new_area
        data["project_contents"] = []
        data["traction_optimised_electrification"] = []
        new_sub_area = MasterArea(**data)
        new_sub_area.project_contents = copy_project_content(sub_area.project_contents, new_sub_area)
        new_sub_area.traction_optimised_electrification = copy_traction_optimised(sub_area.traction_optimised_electrification, new_sub_area)
        new_sub_master_areas.append(new_sub_area)

    return new_sub_master_areas


def copy_traction_optimised(traction_optimised_electrification, area):
    new_copy_traction_optimised = []
    for traction in traction_optimised_electrification:
        data = clone_model(traction)
        data["master_area_id"] = area.id
        data["masterarea"] = area
        new_copy_traction_optimised.append(TractionOptimisedElectrification(**data))

    return new_copy_traction_optimised


def copy_master_area(copy_scenario_id, scenario):
    main_areas_copy_scenario = MasterScenario.query.get(copy_scenario_id).main_areas
    main_areas_to_scenario = []
    all_sub_areas = []
    for area in main_areas_copy_scenario:
        data = clone_model(area)
        data["scenario_id"] = scenario.id
        data["scenario"] = scenario
        data["project_contents"] = []
        data["traction_optimised_electrification"] = []
        data["sub_master_areas"] = []
        new_area = MasterArea(**data)

        new_area.project_contents = copy_project_content(area.project_contents, new_area)

        sub_areas = copy_sub_master_area(area.sub_master_areas, scenario, new_area)
        new_area.sub_master_areas = sub_areas
        all_sub_areas.extend(sub_areas)

        new_area.traction_optimised_electrification = copy_traction_optimised(area.traction_optimised_electrification, new_area)

        main_areas_to_scenario.append(new_area)

    areas = main_areas_to_scenario + all_sub_areas
    return areas


def copy_route_traingroups(copy_scenario_id, to_scenario):
    routes_old = MasterScenario.query.get(copy_scenario_id).routes
    routes_new = []
    for route in routes_old:
        data = clone_model(route)
        data["master_scenario_id"] = to_scenario.id
        data["master_scenario"] = to_scenario
        routes_new.append(RouteTraingroup(**data))

    return routes_new


if __name__ == '__main__':
    pcs = ProjectContent.query.filter(ProjectContent.id.in_(project_content_ids)).all()
    scenario.project_contents = pcs

    if COPY_TRAIN_COST is not None:
        train_costs = copy_train_costs(copy_scenario_id=COPY_TRAIN_COST, scenario=scenario)
        scenario.train_costs = train_costs

    if COPY_AREAS is not None:
        scenario.master_areas = copy_master_area(copy_scenario_id=COPY_AREAS, scenario=scenario)

    if COPY_ROUTING is not None:
        scenario.routes = copy_route_traingroups(copy_scenario_id=COPY_AREAS, to_scenario=scenario)

    db.session.add(scenario)
    db.session.commit()





