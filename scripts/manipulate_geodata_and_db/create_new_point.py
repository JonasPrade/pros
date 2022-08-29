from prosd import db
from prosd.models import RailwayPoint, RailwayNodes, RailwayStation

node_id = 79257

node = RailwayNodes.query.get(node_id)

point_dict = {
    "route_number": 9122,
    "name": "Norderstedt Mitte",
    "type": "Bf",
    "db_kuerzel": "ANDM",
    "coordinates": node.coordinate,
    "node_id": node.id
}

station = RailwayStation.query.filter(RailwayStation.db_kuerzel == point_dict["db_kuerzel"]).first()
if not station:
    station = RailwayStation(
        name=point_dict["name"],
        db_kuerzel=point_dict["db_kuerzel"],
        type=point_dict["type"]
    )

    db.session.add(station)
    db.session.commit()
    db.session.refresh(station)

point = RailwayPoint(
    route_number=point_dict["route_number"],
    name=point_dict["name"],
    type=point_dict["type"],
    db_kuerzel=point_dict["db_kuerzel"],
    coordinates=point_dict["coordinates"],
    node_id=point_dict["node_id"],
    station_id=station.id
)

db.session.add(point)
db.session.commit()

