from prosd.manage_db import shp_import
from prosd import models

filepath_shp = "../../example_data/betriebsstellen_rohdaten/betriebsstellen_point.shp"
column_names = {}
Points = models.RailwayPoint

DbCounty = shp_import.DBManager()

DbCounty.shp_to_railwaypoints(filepath_shp=filepath_shp, column_names=column_names, model=Points, overwrite=True)
