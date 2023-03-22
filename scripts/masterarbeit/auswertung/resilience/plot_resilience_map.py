import geopandas as gpd
import matplotlib.pyplot as plt
import os
import shapely

from prosd.models import RailwayStation, MasterScenario
from prosd.manage_db.version import Version

colors = {
        "SGV-Strecke nicht elektrifiziert": "#dc0073",
        "SGV-Strecke elektrifiziert": "#0a8754",
        "gesperrt": "#008bf8"
    }


def german_border():
    dirname = os.path.dirname(__file__)
    german_border_file = os.path.realpath(os.path.join(dirname, '../../../../example_data/import/border_germany/border_germany.geojson'))
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


def plot_resilience_map(filepath_dir, pc, additional_info, tgs, scenario_id):
    filepath = filepath_dir + f"resilience_map_{pc.id}.png"
    station_kuerzel_list = set()
    scenario = MasterScenario.query.get(scenario_id)
    infra_version = Version(scenario=scenario)

    linestrings = []
    for line in pc.railway_lines:
        linestrings.append(
            {"id": line.id,
             "type": "LineString",
             "properties": {"closed": 'gesperrt'},
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
    for ctype, data in geo_df.groupby('closed'):
        color = colors[ctype]
        data.plot(
            color=color,
            ax=ax,
            label=ctype,
            linewidth=2
        )

    # german_border_df = german_border()
    # german_border_df.plot(ax=ax, color='#BFC0C0', alpha=0.15)

    station_kuerzel_list.update(additional_info["endpoints_closure"])
    station_kuerzel_list.update([tg.first_ocp.ocp.station.db_kuerzel for tg in tgs])
    german_cities_df = german_cities(station_kuerzel_list)
    german_cities_df.plot(ax=ax, color='#dc0073')
    for idx, row in german_cities_df.iterrows():
        plt.annotate(text=row["name"], xy=(row.geometry.x, row.geometry.y))

    linestrings = dict()
    for tg in tgs:
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

    for index, data in geo_df.iterrows():
        catenary = data["catenary"]
        if catenary is False:
            label = 'SGV-Strecke nicht elektrifiziert'
        elif catenary is True:
            label = 'SGV-Strecke elektrifiziert'
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

    ax.legend(loc='upper left', prop={'size':12})
    ax.set(title=f'{pc.name}')
    ax.set_axis_off()
    # plt.show()
    plt.savefig(
        filepath,
        bbox_inches='tight',
        pad_inches=0.5,
        dpi=400
    )

