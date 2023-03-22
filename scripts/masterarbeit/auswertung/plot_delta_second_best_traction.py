import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import RailwayStation, RailwayLine, MasterScenario, ProjectContent, projectcontent_to_group, ProjectGroup, projectcontent_to_line, TimetableTrainGroup


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


def plot_delta_to_efficient_traction(filepath_image_directory, areas, scenario_id):
    filepath = filepath_image_directory + f"second_traction_{scenario_id}.png"

    linestrings = []
    for area in areas:
        cost_all_tractions = area.cost_all_tractions
        first_traction = cost_all_tractions.pop(area.cost_effective_traction)
        second_traction = min(cost_all_tractions, key=cost_all_tractions.get)

        for index, line in enumerate(area.railway_lines):
            linestrings.append(
                {"id": index,
                 "type": "LineString",
                 "properties": {"second_traction": second_traction},
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
    for ctype, data in geo_df.groupby('second_traction'):
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
    ax.set(title=f'Zweitbeste Traktion für Scenario {scenario_id}')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


if __name__ == '__main__':
    scenario_id = 11
    scenario = MasterScenario.query.get(scenario_id)
    areas = scenario.main_areas

    filepath_directory_image = f'../../../example_data/report_scenarios/s_{scenario_id}/files/'
    traction = 'efuel'

    plot_delta_to_efficient_traction(
        filepath_image_directory=filepath_directory_image,
        areas=areas,
        scenario_id=scenario_id
    )
