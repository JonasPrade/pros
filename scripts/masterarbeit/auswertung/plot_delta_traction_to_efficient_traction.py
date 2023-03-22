import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import RailwayStation, RailwayLine, MasterScenario, ProjectContent, projectcontent_to_group, ProjectGroup, projectcontent_to_line, TimetableTrainGroup


colors = {
        "<1": '#fb6107',
        "1 - 1.25": '#cfbe25',
        "1.25 - 1.5": '#cf3925',
        "1.5-2": '#640896',
        ">2": "#070112",
    }


def german_border():
    german_border_file = '../../../example_data/import/border_germany/border_germany.geojson'
    german_border = gpd.read_file(german_border_file)
    return german_border


def plot_delta_to_efficient_traction(filepath_image_directory, areas, traction):
    filepath = filepath_image_directory + f"delta_cost_{traction}.png"

    linestrings = []
    for area in areas:
        cost_all_tractions = area.cost_all_tractions
        if traction in area.cost_all_tractions.keys():
            delta_traction = cost_all_tractions[traction]/cost_all_tractions[area.cost_effective_traction]

            if 1 < delta_traction < 1.25:
                delta_traction_group = "1 - 1.25"
            elif 1.25 <= delta_traction < 1.5:
                delta_traction_group = "1.25 - 1.5"
            elif 1.5 <= delta_traction < 2:
                delta_traction_group = "1.5-2"
            elif 2 <= delta_traction:
                delta_traction_group = ">2"
            elif 1 == delta_traction:
                delta_traction_group = "<1"

            for index, line in enumerate(area.railway_lines):
                linestrings.append(
                    {"id": index,
                     "type": "LineString",
                     "properties": {"delta_traction_group": delta_traction_group},
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
    for ctype, data in geo_df.groupby('delta_traction_group'):
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
    ax.set(title=f'Delta {traction} zu kosteneffizientester Traktion (relativ)')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


if __name__ == '__main__':
    scenario_id = 12
    scenario = MasterScenario.query.get(scenario_id)
    areas = scenario.main_areas

    filepath_directory_image = f'../../../example_data/report_scenarios/s_{scenario_id}/files/'
    traction = 'h2'

    plot_delta_to_efficient_traction(
        filepath_image_directory=filepath_directory_image,
        areas=areas,
        traction=traction
    )
