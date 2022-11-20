import openrouteservice
import shapely
import geoalchemy2
import geojson
import time
import logging

from prosd import db
from prosd.models import RailwayPoint

"""
Gets the height from openrouteservice and add them to the railway_point in th db.
"""

logging.basicConfig(encoding='utf-8', level=logging.INFO)

api_key = "5b3ce3597851110001cf62484dc7d242a69d43098e6f2991ffd6511f"
client = openrouteservice.Client(api_key)

points = RailwayPoint.query.filter(RailwayPoint.height_ors == None).all()

for index, point in enumerate(points):
    coordinate_geojson = point.geojson

    try:
        point_height = openrouteservice.elevation.elevation_point(client=client, format_in='geojson', geometry=coordinate_geojson)
        point.height_ors = point_height["geometry"]["coordinates"][2]
    except KeyError:
        logging.error(f"KeyError for Point {point}")

    db.session.add(point)
    db.session.commit()

    time.sleep(0.6)
    logging.info(f"{index} of {len(points)} finished ({point})")
