import logging

from prosd import db
from prosd.models import RailwayPoint, RailwayNodes

points = RailwayPoint.query.filter(RailwayPoint.node_id == None).all()

for point in points:
    node = RailwayNodes.check_if_nodes_exists_for_coordinate(coordinate = point.coordinates)
    if node is None:
        logging.warning("No node for point " + str(point.name) + "at route " + str(point.route_number))
        continue
    point.node_id = node.id
    db.session.add(point)
    db.session.commit()