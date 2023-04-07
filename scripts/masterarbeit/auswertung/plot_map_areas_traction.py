import shapely
import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import RailwayStation, RailwayLine, MasterScenario, ProjectContent, projectcontent_to_group, ProjectGroup, projectcontent_to_line, TimetableTrainGroup
from prosd.manage_db.version import Version
from prosd import db

colors = {
        "electrification": '#fb6107',
        "battery": '#0a8754',
        "optimised_electrification": '#dc0073',
        "h2": "#008bf8",
        "elektrifiziert": "#0A8754",
        "nicht elektrifiziert": "#DC0073",
        "BVWP 2030": "#0a8754",
        "Elektrische Güterbahn": "#008bf8",
    }


def german_border():
    german_border_file = '../../../example_data/import/border_germany/border_germany.geojson'
    german_border = gpd.read_file(german_border_file)
    return german_border


def german_cities(station_id_list):
    stations = RailwayStation.query.filter(RailwayStation.db_kuerzel.in_(station_id_list)).all()
    points = []
    for station in stations:
        geometry = shapely.wkb.loads(station.railway_points[0].coordinates.desc, hex=True)
        points.append(
            {"id": station.id,
             "type": "LineString",
             "properties": {"name": station.name, "db_kuerzel": station.db_kuerzel},
             "geometry": geometry
             }
        )

    geo_features = {
        "type": "FeatureCollection",
        "features": points
    }

    stations_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    return stations_df


def plot_map_traction(filepath_image_directory, areas):
    filepath = filepath_image_directory + "deutschland_map.png"

    linestrings = []
    for area in areas:
        traction = area.cost_effective_traction
        for index, line in enumerate(area.railway_lines):
            linestrings.append(
                {"id": index,
                 "type": "LineString",
                 "properties": {"cost_effective_traction": traction},
                 "geometry": line.geojson
                 }
            )

    geo_features = {
        "type": "FeatureCollection",
        "features": linestrings
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400
    for ctype, data in geo_df.groupby('cost_effective_traction'):
        color = colors[ctype]
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=1.5
        )
    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size':12})
    ax.set(title='Traktionswahl Deutschland ohne optimierte Elektrifizierung')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )
    return filepath


def plot_map_traction_without_optimised_electrificaton(filepath_image_directory, areas):
    filepath = filepath_image_directory + "traction_map_no_optimised.png"

    linestrings = []
    for area in areas:
        traction = area.cost_effective_traction
        if traction == 'optimised_electrification':
            sub_areas = area.sub_master_areas
            for sub_area in sub_areas:
                sub_area_traction = sub_area.cost_effective_traction
                for index, line in enumerate(sub_area.railway_lines):
                    linestrings.append(
                        {"id": index,
                         "type": "LineString",
                         "properties": {"cost_effective_traction": sub_area_traction},
                         "geometry": line.geojson
                         }
                    )
        else:
            for index, line in enumerate(area.railway_lines):
                linestrings.append(
                    {"id": index,
                     "type": "LineString",
                     "properties": {"cost_effective_traction": traction},
                     "geometry": line.geojson
                     }
                )

    geo_features = {
        "type": "FeatureCollection",
        "features": linestrings
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400
    for ctype, data in geo_df.groupby('cost_effective_traction'):
        color = colors[ctype]
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=1.5
        )
    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size':12})
    ax.set(title='Traktionswahl Deutschland')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )
    return filepath


def plot_sgv_map(scenario_id, filepath_image_directory, areas, titlename):
    filepath = filepath_image_directory + "sgv_map.png"
    linestrings = dict()
    scenario = MasterScenario.query.get(scenario_id)
    infra_version = Version(scenario=scenario)

    for area in areas:
        # traction = area.cost_effective_traction
        for index, tg in enumerate(area.traingroups):
            if tg.category.transport_mode == 'sgv':
                rw_lines = tg.railway_lines_scenario(scenario_id)
                for line in rw_lines:
                    line_infra_version = infra_version.get_railwayline_model(line.id)
                    if line.id in linestrings:
                        usage = linestrings[line.id]["properties"]["count_usage"]
                        linestrings[line.id] =  {"id": line.id,
                             "type": "LineString",
                             "properties": {"catenary": line_infra_version.catenary, "count_usage": usage+1},
                             "geometry": line.geojson
                             }
                    else:
                        linestrings[line.id] = {"id": line.id,
                                                "type": "LineString",
                                                "properties": {"catenary": line_infra_version.catenary,
                                                               "count_usage": 1},
                                                "geometry": line.geojson
                                                }

    linestring_for_geo = list(linestrings.values())
    geo_features = {
        "type": "FeatureCollection",
        "features": linestring_for_geo
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400

    for index, data in geo_df.iterrows():
        catenary = data["catenary"]
        if catenary is False:
            label = 'nicht elektrifiziert'
        elif catenary is True:
            label ='elektrifiziert'
        color = colors[label]
        count_usage = data["count_usage"]
        series = gpd.GeoSeries(
            data=data["geometry"],
            crs="EPSG:4326"
        )
        series.plot(
            ax=ax,
            color=color,
            linewidth=count_usage
        )

    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title=titlename)
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


def plot_all_sgv_map(scenario_id):
    filepath = '../../../example_data/report_scenarios/common_maps/all_spfv_ausgangsszenario.png'
    linestrings = dict()
    scenario = MasterScenario.query.get(scenario_id)
    infra_version = Version(scenario=scenario)

    traingroups = TimetableTrainGroup.query.all()

    for index, tg in enumerate(traingroups):
        if tg.category.transport_mode == 'spfv':
            rw_lines = tg.railway_lines_scenario(scenario_id)
            for line in rw_lines:
                line_infra_version = infra_version.get_railwayline_model(line.id)
                if line.id in linestrings:
                    usage = linestrings[line.id]["properties"]["count_usage"]
                    linestrings[line.id] =  {"id": line.id,
                         "type": "LineString",
                         "properties": {"catenary": line_infra_version.catenary, "count_usage": usage+1},
                         "geometry": line.geojson
                         }
                else:
                    linestrings[line.id] = {"id": line.id,
                                            "type": "LineString",
                                            "properties": {"catenary": line_infra_version.catenary,
                                                           "count_usage": 1},
                                            "geometry": line.geojson
                                            }

    linestring_for_geo = list(linestrings.values())
    geo_features = {
        "type": "FeatureCollection",
        "features": linestring_for_geo
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400

    for index, data in geo_df.iterrows():
        catenary = data["catenary"]
        if catenary is False:
            label = 'nicht elektrifiziert'
        elif catenary is True:
            label ='elektrifiziert'
        color = colors[label]
        count_usage = data["count_usage"]
        series = gpd.GeoSeries(
            data=data["geometry"],
            crs="EPSG:4326"
        )
        series.plot(
            ax=ax,
            color=color,
            linewidth=count_usage
        )

    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title='Ausgangssituation Strecken mit Schienenpersonenfernverkehr')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


def plot_all_category_map(category_transport_mode):
    ffilepath = f'../../../example_data/report_scenarios/common_maps/all_{category_transport_mode}_ausgangsszenario.png'
    linestrings = dict()
    scenario = MasterScenario.query.get(scenario_id)
    infra_version = Version(scenario=scenario)

    traingroups = TimetableTrainGroup.query.all()

    for index, tg in enumerate(traingroups):
        if tg.category.transport_mode == 'category_transport_mode':
            rw_lines = tg.railway_lines_scenario(scenario_id)
            for line in rw_lines:
                line_infra_version = infra_version.get_railwayline_model(line.id)
                if line.id in linestrings:
                    usage = linestrings[line.id]["properties"]["count_usage"]
                    linestrings[line.id] =  {"id": line.id,
                         "type": "LineString",
                         "properties": {"catenary": line_infra_version.catenary, "count_usage": usage+1},
                         "geometry": line.geojson
                         }
                else:
                    linestrings[line.id] = {"id": line.id,
                                            "type": "LineString",
                                            "properties": {"catenary": line_infra_version.catenary,
                                                           "count_usage": 1},
                                            "geometry": line.geojson
                                            }

    linestring_for_geo = list(linestrings.values())
    geo_features = {
        "type": "FeatureCollection",
        "features": linestring_for_geo
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400

    for index, data in geo_df.iterrows():
        catenary = data["catenary"]
        if catenary is False:
            label = 'nicht elektrifiziert'
        elif catenary is True:
            label ='elektrifiziert'
        color = colors[label]
        count_usage = data["count_usage"]
        series = gpd.GeoSeries(
            data=data["geometry"],
            crs="EPSG:4326"
        )
        series.plot(
            ax=ax,
            color=color,
            linewidth=count_usage
        )

    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title=f'Ausgangssituation Strecken {category_transport_mode}')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


def plot_bvwp():
    filepath = '../../../example_data/report_scenarios/common_maps/bvwp.png'
    station_id_list = [
        'AST',
        'ABX',
        'AL',
        'HH',
        'MH',
        'NN',
        'NHO',
        'TU',
        'NRH',
        'LM',
        'WA',
        'UWM',
        'HU',
        'DC',
        'UL',
        'EDG',
        'LNX',
        'UGT',
        'ETIE',
        'LNOE',
        'HW',
        'AROG',
        'LW',
        'LOE',
        'HHM'
    ]

    pcs = db.session.query(ProjectContent).join(projectcontent_to_group).join(ProjectGroup).join(projectcontent_to_line).join(RailwayLine).filter(
        ProjectGroup.id == 1,
        ProjectContent.elektrification == True,
        ProjectContent.priority.in_(['Vordringlicher Bedarf (VB)', 'Vordringlicher Bedarf - Engpassbeseitigung (VB-E)'])
    ).all()

    pcs.extend(
        db.session.query(ProjectContent).join(projectcontent_to_group).join(ProjectGroup).join(
            projectcontent_to_line).join(RailwayLine).filter(
            ProjectGroup.id == 5,
            ProjectContent.elektrification == True
        ).all()
    )

    linestrings = list()
    for pc in pcs:
        projectgroup = pc.projectcontent_groups[0].name
        for index, line in enumerate(pc.railway_lines):
            linestrings.append(
                {"id": index,
                 "type": "LineString",
                 "properties": {"type_pc": 'electrification', "projectgroup": projectgroup},
                 "geometry": line.geojson
                 }
            )

    geo_features = {
        "type": "FeatureCollection",
        "features": linestrings
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400

    for ctype, data in geo_df.groupby('projectgroup'):
        color = colors[ctype]
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=2
        )

    german_cities_df = german_cities(station_id_list)
    german_cities_df.plot(ax=ax, color='#dc0073')
    for idx, row in german_cities_df.iterrows():
        plt.annotate(text=row["name"], xy=(row.geometry.x, row.geometry.y))

    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)

    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title='Projekte Elektrifizierung BVWP')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


def plot_route_train(tg_id, scenario_id):
    filepath = f'../../../example_data/report_scenarios/traingroups/{tg_id}.png'

    tg = TimetableTrainGroup.query.get(tg_id)
    lines = tg.railway_lines_scenario(scenario_id)

    linestrings = list()
    for line in lines:
        linestrings.append(
            {"id": line.id,
             "type": "LineString",
             "properties": {"traingroup": tg},
             "geometry": line.geojson
             }
        )

    geo_features = {
        "type": "FeatureCollection",
        "features": linestrings
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400
    for ctype, data in geo_df.groupby('traingroup'):
        color = '#dc0073'
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=2
        )
    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title='Projekte Elektrifizierung BVWP')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


if __name__ == '__main__':
    scenario_id = 1
    scenario = MasterScenario.query.get(scenario_id)
    areas = scenario.main_areas
    # plot_map_traction_without_optimised_electrificaton(
    #     filepath_image_directory=f'../../../example_data/report_scenarios/s_{scenario_id}/files/',
    #     areas=areas
    # )

    # traingroups = [area.traingroups for area in areas]
    # plot_sgv_map(
    #     scenario_id=scenario_id,
    #     filepath_image_directory=f'../../../example_data/report_scenarios/s_{scenario_id}/files/',
    #     areas=areas
    # )
    plot_all_sgv_map(
        scenario_id=scenario_id
    )
    # plot_all_category_map(
    #     category_transport_mode='spnv'
    # )
    # plot_map_traction(
    #     filepath_image_directory=f'../../../example_data/report_scenarios/s_{scenario_id}/files/',
    #     areas=areas
    # )

    # plot_bvwp()

    # tg_id = 'tg_110_x0020_G_x0020_2518_117566'
    # plot_route_train(tg_id, scenario_id)


