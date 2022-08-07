from prosd.manage_db.shp_import import DBManager
from prosd.models import RailwayPoint
filepath_shp = "/Users/jonas/PycharmProjects/pros/example_data/betriebsstellen/betriebsstellen_point.shp"
model = RailwayPoint

db_manager = DBManager()
db_manager.shp_to_railwaypoints(filepath_shp=filepath_shp, model=model, overwrite=True)