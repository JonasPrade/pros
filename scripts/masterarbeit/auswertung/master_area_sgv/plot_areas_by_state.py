import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import MasterArea, States, RailwayLine, railwaylines_to_masterareas
from prosd import db
import sqlalchemy
import geoalchemy2
import shapely


def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)


def plot_areas_for_state(areas, filepath_image_directory, area_numbers, state):
    filepath = filepath_image_directory + f"{state.name}.png"
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

    features = []
    for polygon in shapely.wkb.loads(state.polygon.desc, hex=True):
        feature= {
            "type": "Polygon",
            "properties": {"name": state.name},
            "geometry": polygon
        }
        features.append(feature)

    state_features = {
        "type":"FeatureCollection",
        "features": features
    }

    state_df = gpd.GeoDataFrame.from_features(
        state_features
    )
    state_df.set_crs(epsg=4326, inplace=True)

    f, ax = plt.subplots(1, figsize=(15, 18))
    plt.rcParams['figure.dpi'] = 400

    state_df.plot(ax=ax, color='#BFC0C0', alpha=0.4)

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

    ax.legend(loc='upper left', prop={'size': 12})
    ax.set(title=f'Untersuchungsgebiete {state.name}')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


if __name__ == '__main__':
    filepath_image_directory = '../../../../example_data/report_scenarios/states/'
    scenario_id = 4
    areas = []
    state_name = 'Baden-Württemberg'
    state = States.query.filter(States.name == state_name).one()
    railway_lines = RailwayLine.query.filter(
    geoalchemy2.func.ST_Intersects(
            RailwayLine.coordinates, state.polygon
        )
    ).all()
    areas = MasterArea.query.join(railwaylines_to_masterareas).join(RailwayLine).filter(
        MasterArea.scenario_id == scenario_id,
        MasterArea.superior_master_id == None,
        RailwayLine.id.in_([line.id for line in railway_lines])
    ).all()

    area_numbers = {area.id:index for index, area in enumerate(areas)}

    plot_areas_for_state(
        areas=areas,
        filepath_image_directory=filepath_image_directory,
        state=state,
        area_numbers=area_numbers
    )
