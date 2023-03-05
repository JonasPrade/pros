import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import MasterArea, RailwayLine, MasterScenario
from prosd.manage_db.version import Version

colors = {
        "electrification": '#fb6107',
        "battery": '#0a8754',
        "optimised_electrification": '#dc0073',
        "h2": "#008bf8",
    }


def german_border():
    german_border_file = '../../../example_data/import/border_germany/border_germany.geojson'
    german_border = gpd.read_file(german_border_file)
    return german_border


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


def plot_sgv_map(scenario_id, filepath_image_directory, areas):
    filepath = filepath_image_directory + "sgv_map.png"
    linestrings = dict()
    scenario = MasterScenario.query.get(scenario_id)
    infra_version = Version(scenario=scenario)

    for area in areas:
        # traction = area.cost_effective_traction
        for index, tg in enumerate(area.traingroups):
            rw_lines = tg.railway_lines_scenario(scenario_id)
            for line in rw_lines:
                line_infra_version = infra_version.get_railwayline_model(line.id)
                linestrings["line.id"] =  {"id": line.id,
                     "type": "LineString",
                     "properties": {"catenary": line_infra_version.catenary},
                     "geometry": line.geojson
                     }

    geo_features = {
        "type": "FeatureCollection",
        "features": linestrings.values()
    }

    geo_df = gpd.GeoDataFrame.from_features(
        geo_features,
    )
    geo_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400
    for ctype, data in geo_df.groupby('catenary'):
        data.plot(
            ax=ax,
            label=ctype,
            linewidth=1.5
        )
    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)
    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title='Traktionswahl Deutschland')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


if __name__ == '__main__':
    scenario_id = 4
    scenario = MasterScenario.query.get(scenario_id)
    areas = scenario.main_areas
    traingroups = [area.traingroups for area in areas]
    plot_sgv_map(
        scenario_id=scenario_id,
        filepath_image_directory=f'../../../example_data/report_scenarios/s_{scenario_id}/files/',
        areas=areas
    )
    # plot_map_traction(
    #     filepath_image_directory=f'../../../example_data/report_scenarios/s_{scenario_id}/files/',
    #     areas=areas
    # )


