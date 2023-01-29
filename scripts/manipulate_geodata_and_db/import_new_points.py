from prosd import db
from prosd.models import RailwayPoint, RailwayNodes, RailwayStation, RailMlOcp
from prosd.graph import railgraph

import pandas

filepath = '../../example_data/import/points/point_import_28012023.xlsx'
df = pandas.read_excel(filepath)

for index, row in df.iterrows():
    point_dict = row.to_dict()
    node = RailwayNodes.query.get(point_dict["node_id"])
    point_dict["coordinates"] = node.coordinate

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

    rg = railgraph.RailGraph()
    rg.delete_graph_route(route_number=point_dict["route_number"])

