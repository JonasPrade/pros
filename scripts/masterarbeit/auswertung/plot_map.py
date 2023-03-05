import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import MasterArea, RailwayLine, MasterScenario


def plot_map(scenario_id, filepath_image_directory, areas):
    filepath = filepath_image_directory + "deutschland_map.png"

    colors = {
        "electrification": '#00b6b5',
        "battery": '#7DDF64',
        "optimised_electrification": '#ff0064',
        "h2": "#da539"
    }

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

    german_border_file = '../../../example_data/import/border_germany/border_germany.geojson'
    german_border = gpd.read_file(german_border_file)

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
    german_border.plot(ax=ax, color='#BFC0C0', alpha=0.2)
    ax.legend(loc='upper left', prop={'size':12})
    ax.set(title='Traktionswahl Deutschland')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=300
    )
    return filepath

if __name__ == '__main__':
    scenario_id = 4
    scenario = MasterScenario.query.get(scenario_id)
    areas = scenario.master_areas
    plot_map(
        scenario_id=scenario_id,
        filepath_image_directory=f'../../../example_data/report_scenarios/s_{scenario_id}/files/s-{scenario_id}_deutschland_map',
        areas=areas
    )

