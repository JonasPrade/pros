from prosd import db
from prosd.models import ProjectContent, ProjectGroup, RailwayStation, Text, RailwayLine
from prosd.graph.railgraph import RailGraph

name = "ABS Uelzen – Stendal – Magdeburg – Halle (Ostkorridor Nord): Knoten Stendal"
superior_project_id = 29
project_number = "2-018-V01 TM8"
description="Einbindung des zweiten Gleis (Uelzen – Stendal) in den Knoten; Anpassung und Erweiterung der Gleisanlagen; Schaffung von Überholmöglichkeiten für 740m lange Güterzüge; Anpassung des Gleisbogens in Richtung Magdeburg (von 60 km/h auf 80 km/h); Anpassung Leit- und Sicherungstechnik"
reason_project = "Die Führung von Güterzügen zwischen dem Hamburger Hafen und Mitteldeutschland über Uelzen, Salzwedel und Stendal ist gegenüber dem alternativen Weg über Büchen und Wittenberge rd. 40 km kürzer. Im Vergleich mit der Führung über Uelzen, Celle und Braunschweig beträgt die Verkürzung sogar rd. 95 km. Da die Strecke zwischen Uelzen und Stendal jedoch nur abschnittsweise zweigleisig ausgebaut ist, sind die Nutzungsmöglichkeiten durch den Güterverkehr eingeschränkt. In den eingleisigen Abschnitten Uelzen – Wieren – Salzwedel und Hohenwulsch – Stendal stehen aufgrund des vorhandenen Bedienungsangebots im Schienenpersonennahverkehr nur sehr begrenzte Kapazitäten für Güterzüge zur Verfügung. Zur Auflösung der Engpässe ist daher ein zweigleisiger Vollausbau notwendig. So kann die Strecke die Nachfrage im Güterverkehr aufnehmen und es können die mit der Laufwegsverkürzung verbundenen Angebotsverbesserungen durch Transportkosteneinsparung erzielt werden. Im weiteren Verlauf zwischen Stendal, Magdeburg und Halle kommt es aufgrund großer Blockabstände auch heute schon zu Überlastungen. Durch Blockverdichtungen soll hier eine Besserung der Situation erzielt werden."
project_group_ids = [1, 7]
stations = ["LS"]
lines = [
    [],
]  # a list which contains list. They are "from", "to" and "via" (list) stations
existing_text_ids = [11]

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
pc.second_track = True
pc.platform = True
pc.sgv740m = True
pc.increase_speed = True
pc.new_vmax = 80

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