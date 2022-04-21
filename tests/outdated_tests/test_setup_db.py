import prosd

# TODO: Add a config.py to specifiy which db is used!

filepath_shp = '../../example_data/monorail/shp/monorail.shp'
column_names_railwaylines = {
    "id": "id",
    "mifcode": "mifcode",
    "streckennummer": "streckennu",
    "direction": "direction",
    "length": "length",
    "from_km": "from_km",
    "to_km": "to_km",
    "electrified": "electrifie",
    "number_tracks": "number_tracks",
    "vmax": "vmax",
    "type_of_transport": "type_of_transport",
    "coordinates": "geometry"
}

db_manager = prosd.manage_db.DBManager()
db_manager.shp_to_railwaylines(filepath_shp, column_names_railwaylines, overwrite=True)
