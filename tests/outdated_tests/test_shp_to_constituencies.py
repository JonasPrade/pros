from prosd.manage_db import shp_import
from prosd import models

filepath_shp = '/Users/jonas/PycharmProjects/pros/example_data/constituencies/Geometrie_Wahlkreise_18DBT_VG1000.shp'
column_names = {}
Constituencies = models.Constituencies
State = models.States

DbCounty = shp_import.DBManager()

DbCounty.shp_to_constituencies(filepath_shp=filepath_shp, column_names=column_names, model=Constituencies, model_state=State, overwrite=True)