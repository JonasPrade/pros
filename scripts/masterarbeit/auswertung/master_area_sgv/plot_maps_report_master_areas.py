import geopandas as gpd
import matplotlib.pyplot as plt

from prosd.models import MasterScenario, MasterArea, TimetableTrain, TimetableTrainGroup, TimetableTrainPart, TimetableCategory, traingroups_to_masterareas

def german_border():
    german_border_file = '../../../../example_data/import/border_germany/border_germany.geojson'
    german_border_gpd = gpd.read_file(german_border_file)
    return german_border_gpd


def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)


def plot_areas(areas, filepath_image_directory, scenario_name, area_numbers):
    filepath = filepath_image_directory + "master_areas_sgv.png"
    linestrings = dict()

    for index_area, area in enumerate(areas):
        # traction = area.cost_effective_traction
        for index, rw_lines in enumerate(area.railway_lines):
            linestrings[rw_lines.id] = {"id": rw_lines.id,
                 "type": "LineString",
                 "properties": {"master_area": area_numbers[area.id]},
                 "geometry": rw_lines.geojson
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

    cmap = get_cmap(len(areas))
    for ctype, data in geo_df.groupby('master_area'):
        color = cmap(ctype)
        centroid = data.dissolve().centroid
        x = centroid.x
        y = centroid.y
        xy = (x, y)
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=2
        )
        plt.annotate(text=str(ctype), xy=(xy))

    german_border_df = german_border()
    german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.2)
    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title=f'Untersuchungsgebiete SGV {scenario_name}')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )

