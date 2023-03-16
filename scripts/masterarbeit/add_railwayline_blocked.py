import json

from prosd.graph import railgraph, routing
from prosd.models import MasterScenario, RailwayLine, TimetableTrainGroup, RouteTraingroup, ProjectContent, TimetableTrain, RailwayStation, TimetableTrainPart, TimetableCategory
from prosd.manage_db import version
from prosd import db


# Create a scenario -> create_scenario()
scenario_id = 7
rg = railgraph.RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
scenario = MasterScenario.query.get(scenario_id)

filepath_block = f'../../example_data/railgraph/blocked_scenarios/s-{scenario_id}.json'


def save_additional_project_info(pc, additional_ignore_ocp, traingroups_to_reroute):
    """

    :param pc:
    :param additional_ignore_ocp: additional ocp that gets ignored for routing
    :return:
    """
    try:
        with open(filepath_block, 'r') as openfile:
            geojson_data = json.load(openfile)
    except json.decoder.JSONDecodeError:
        geojson_data = dict()

    geojson_data[pc.id] = {
        "additional_ignore_ocp": additional_ignore_ocp,
        "traingroups_to_reroute": traingroups_to_reroute
    }

    with open(filepath_block, 'w') as outfile:
        json.dump(geojson_data, outfile)


def read_additional_project_info():
    with open(filepath_block, 'r') as openfile:
        geojson_data = json.load(openfile)

    return geojson_data


def create_project():
    from_ocp = 'ALBG'
    to_ocp = 'HU'
    stations_via = []
    reroute_train_categories = ['sgv', 'spfv']
    project_content_number = f"s-{scenario_id} Sperrung {from_ocp} – {to_ocp}"
    project_content_name = 'Sperrung Lüneburg – Uelzen'
    additional_ignore_ocp = [
        'ASTE',
        'AASA',
        'AWI',
        'ARH',
        'ABAD',
        'ALBG',
        'ADEV'
        'HGAR',
        'HESD',
        'HUNL',
        'HSUD',
        'HKSU'
    ]

    infra_version = version.Version(scenario=scenario)
    route = routing.GraphRoute(graph=graph, infra_version=infra_version)
    path = route.route_line(station_from=from_ocp, station_to=to_ocp, stations_via=stations_via)

    blocked_lines_id = path['edges']
    blocked_lines = RailwayLine.query.filter(RailwayLine.id.in_(blocked_lines_id)).all()

    blocked_ocp = set()
    blocked_ocp.update(RailwayStation.query.filter(RailwayStation.db_kuerzel.in_(additional_ignore_ocp)).all())

    for stations in [line.stations for line in blocked_lines]:
        for station in stations:
            if station.db_kuerzel == from_ocp or station.db_kuerzel == to_ocp:
                continue
            blocked_ocp.add(station)

    pc = ProjectContent(
        name=project_content_name,
        project_number=project_content_number,
        closure=True
    )
    pc.railway_lines = blocked_lines
    pc.railway_stations = list(blocked_ocp)
    db.session.add(pc)
    db.session.commit()

    tgs = TimetableTrainGroup.query.join(RouteTraingroup).join(TimetableTrain).join(TimetableTrainPart).join(
        TimetableCategory).filter(
        RouteTraingroup.master_scenario_id == scenario_id,
        RouteTraingroup.railway_line_id.in_(blocked_lines_id),
        TimetableCategory.transport_mode.in_(reroute_train_categories)
    ).all()

    save_additional_project_info(pc=pc, additional_ignore_ocp=additional_ignore_ocp, traingroups_to_reroute=tgs)


def reroute_traingroups():
    infra_version = version.Version(scenario=scenario)

    data = read_additional_project_info()
    traingroups = []
    blocked_ocps = []
    for key, value in data.items():
        pc = ProjectContent.query.get(key)
        infra_version.add_projectcontents_to_version_temporary(
            pc_list=[pc],
            update_infra=True,
            use_subprojects=False
        )
        traingroups.extend(value["traingroups_to_reroute"])
        blocked_ocps.extend(value["additional_ignore_ocp"])

    route = routing.GraphRoute(graph=graph, infra_version=infra_version)

    for tg in traingroups:
        route.line(
            traingroup=tg,
            save_route=True,
            force_recalculation=True,
            ignore_ocps=set([station.db_kuerzel for station in blocked_ocps])
        )


def reroute_traingroups_without_blocked_lines():
    infra_version = version.Version(scenario=scenario)
    data = read_additional_project_info()
    traingroups = []
    for key, value in data.items():
        pc = ProjectContent.query.get(key)
        traingroups.extend(value["traingroups_to_reroute"])

    route = routing.GraphRoute(graph=graph, infra_version=infra_version)
    for tg in traingroups:
        route.line(
            traingroup=tg,
            save_route=True,
            force_recalculation=True
        )


if __name__ == '__main__':
    reroute_traingroups_without_blocked_lines()

