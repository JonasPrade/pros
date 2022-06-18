from prosd.manage_db import shp_import
from prosd import models

filepath_shp = '../../example_data/counties/georef-germany-kreis-millesime.shp'
column_names = {}
Counties = models.Counties
State = models.States

DbCounty = shp_import.DBManager()

DbCounty.shp_to_counties(filepath_shp=filepath_shp, column_names=column_names, model=Counties, model_state=State, overwrite=True)