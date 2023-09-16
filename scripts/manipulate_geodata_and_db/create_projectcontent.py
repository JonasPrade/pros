from prosd import db
from prosd.models import ProjectContent, ProjectGroup, RailwayStation, Text, RailwayLine
from prosd.graph.railgraph import RailGraph

name = "ABS/NBS Hamburg – Lübeck – Puttgarden: Fehmarnsundtunnel"
superior_project_id = 18
project_number = "2-011-V01 - Fehmarnsundtunnel"
description="Bauabschnitt Fehmarnsundtunnel"
reason_project = "Mit dem am 3. September 2008 unterzeichneten Staatsvertrag zwischen Deutschland und Dänemark wurde die Errichtung einer festen Fehmarnbeltquerung beschlossen. Der Staatsvertrag sieht vor, dass Dänemark die Finanzierung des Querungsbauwerkes inklusive der zugehörigen Rampen- und Anschlussbereiche übernimmt. Die Bundesrepublik Deutschland verpflichtet sich zur Finanzierung und zum Ausbau der Hinterlandanbindung auf deutscher Seite. Diese besteht aus dem zweigleisigen Ausbau und der Elektrifizierung der Strecke Lübeck – Puttgarden sowie dem Neubau der Fehmarnsundquerung. Die Überholgleise im Gesamtabschnitt Hamburg – Lübeck – Puttgarden sind dabei für Züge mit einer Länge von 835 m auszulegen. Die Erhöhung der Fahrgeschwindigkeiten auf bis zu 160 km/h führt im Personenverkehr zur Reduzierung der Fahrzeiten zwischen Hamburg und Kopenhagen. Im Güterverkehr können nach der Elektrifizierung der Strecke die aktuell über Flensburg und die Jütlandlinie geführten Verkehre in Richtung Ostdänemark und Schweden über den Fehmarnbelttunnel geführt werden. Der sich so ergebende Fahrweg über Lübeck und Puttgarden in Richtung Schweden ist gegenüber der aktuellen Route um 140 km kürzer und somit mit deutlichen Transportkosteneinsparungen verbunden."
project_group_ids = [1, 7]
stations = []
lines = [
    [],
]  # a list which contains list. They are "from", "to" and "via" (list) stations
existing_text_ids = [14]

pc = ProjectContent(
    name=name,
    project_number=project_number,
    superior_project_content_id=superior_project_id,
    description=description,
    reason_project=reason_project
)

# change that
pc.effects_passenger_local_rail= True
pc.effects_passenger_long_rail = False
pc.effects_cargo_rail = True

# add the properties of project here
pc.nbs = True

# progress
pc.lp_12 = 1

### no editings below this line needed ###
projectgroups = ProjectGroup.query.filter(ProjectGroup.id.in_(project_group_ids)).all()
pc.projectcontent_groups = projectgroups

# railway_stations
for station_id in stations:
    station = RailwayStation.query.filter(RailwayStation.db_kuerzel == station_id).scalar()
    pc.railway_stations.append(station)

# railway_lines
rg = RailGraph()
graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
rw_lines = []
for relation in lines:
    if len(relation) == 0:
        continue
    path = rg.shortest_path_between_stations(graph=graph, station_from=relation[0], station_to=relation[1], stations_via=relation[2])
    rw_lines.extend(path["edges"])

railway_lines = RailwayLine.query.filter(RailwayLine.id.in_(rw_lines)).all()
pc.railway_lines = railway_lines


# textes
textes = Text.query.filter(Text.id.in_(existing_text_ids)).all()
pc.texts = textes

db.session.add(pc)
db.session.commit()
db.session.refresh(pc)

pc.generate_geojson()
pc.compute_centroid()

db.session.add(pc)
db.session.commit()