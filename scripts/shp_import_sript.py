from prosd.manage_db.shp_import import DBManager
from prosd.models import RailwayPoint
filepath_shp = "/example_data/betriebsstellen_rohdaten/betriebsstellen_point.shp"
model = RailwayPoint

db_manager = DBManager()
db_manager.shp_to_railwaypoints(filepath_shp=filepath_shp, model=model, overwrite=True)