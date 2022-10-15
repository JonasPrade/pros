import geopandas
import geoalchemy2

from prosd import db
from prosd.models import RailwayLine
from prosd.graph.railgraph import RailGraph

route_number = 6768
FILEPATH = '../../example_data/import/shp_railway_lines/{route_number}.shp'.format(route_number=route_number)

shp = geopandas.read_file(FILEPATH)

number_tracks = 'eingleisig'
catenary = False
conductor_rail = False
voltage = None
dc_ac = None
vmax = None
type_of_transport = "Pz/Gz-Bahn"
gauge = 1435
abs_nbs = "ks"
railway_infrastructure_company = 38

# preparing coordinate
shp['coord'] = shp['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
shp.drop('geometry', 1, inplace=True)
shp = shp.rename(columns={"coord": "geometry"})

# TODO: Update to new columns electrification
objects = []
for index, row in shp.iterrows():
    railway_line_input = RailwayLine(
        coordinates=row.geometry,
        number_tracks=number_tracks,
        catenary=catenary,
        conductor_rail=conductor_rail,
        voltage=voltage,
        dc_ac=dc_ac,
        route_number=route_number,
        vmax=vmax,
        type_of_transport=type_of_transport,
        gauge=gauge,
        abs_nbs=abs_nbs,
        railway_infrastructure_company=railway_infrastructure_company
    )
    objects.append(railway_line_input)

db.session.bulk_save_objects(objects)
db.session.commit()

rg = RailGraph()
rg.create_nodes_new_railwaylines()
rg.delete_graph_route(route_number=route_number)
