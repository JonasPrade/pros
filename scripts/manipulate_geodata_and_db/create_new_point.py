from prosd import db
from prosd.models import RailwayPoint, RailwayNodes, RailwayStation, RailMlOcp
from prosd.graph import railgraph

node_id = 80229

node = RailwayNodes.query.get(node_id)

point_dict = {
    "route_number": 1280,
    "name": "Hamburg-Rothenburgsort",
    "type": "Hp",
    "db_kuerzel": "AHROO",
    "coordinates": node.coordinate,
    "node_id": node.id
}

# TODO: Calculate height and add that also

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

# check if a RailMlOcp is also that new station
ocp = RailMlOcp.query.filter(RailMlOcp.code==point_dict["db_kuerzel"]).scalar()
if ocp is not None:
    ocp.station_id = station.id
    db.session.add(ocp)
    db.session.commit()

railgraph = railgraph.RailGraph()
railgraph.delete_graph_route(route_number=point_dict["route_number"])

