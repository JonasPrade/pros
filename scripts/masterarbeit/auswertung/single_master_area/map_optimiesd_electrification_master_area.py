import geopandas as gpd
import matplotlib.pyplot as plt
from prosd.models import MasterArea, RailwayStation
import shapely

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
    stations_df.set_crs(epsg=4326, inplace=True)
    return stations_df


def plot_optimised_electrification(area, filepath_image_directory, station_ignore_list):
    filepath = filepath_image_directory + f"map_{area.id}_optimised_electrification.png"
    linestrings = dict()

    # to plot some stations for orientation -> get the starting ocps for the spnv area
    station_list = set()
    for tg in area.traingroups:
        if tg.category.transport_mode == 'spnv':
            station_list.add(tg.first_ocp.ocp.station.db_kuerzel)
            station_list.add(tg.last_ocp.ocp.station.db_kuerzel)

    station_list = station_list - station_ignore_list

    for sub_area in area.sub_master_areas:
        traction = sub_area.cost_effective_traction
        for index, rw_lines in enumerate(sub_area.railway_lines):
            linestrings[rw_lines.id] = {"id": rw_lines.id,
                 "type": "LineString",
                 "properties": {"traction": traction},
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

    for ctype, data in geo_df.groupby('traction'):
        color = colors[ctype]
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=2
        )

    german_cities_df = german_cities(station_list)
    german_cities_df.plot(ax=ax, color='#dc0073')
    for idx, row in german_cities_df.iterrows():
        plt.annotate(text=row["name"], xy=(row.geometry.x, row.geometry.y))

    ax.legend(loc='upper right', prop={'size': 12})
    ax.set(title=f'Untersuchungsgebiet {area.id} Optimierte Elektrifizierung')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )


if __name__ == '__main__':
    filepath_image_directory = '../../../../example_data/report_scenarios/maps_optimised_electrification/'
    area_id = 17760
    area = MasterArea.query.get(area_id)
    station_ignore_list = {
        "NHR",
        "NHAN",
        "NSS",
        "DH",
        "WR",
        "AAN",
        "YARSM",
        "AEU"
    }

    plot_optimised_electrification(
        area=area,
        filepath_image_directory=filepath_image_directory,
        station_ignore_list=station_ignore_list
    )
