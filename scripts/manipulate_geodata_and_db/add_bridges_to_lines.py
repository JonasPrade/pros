import geoalchemy2

from prosd import db
from prosd.models import RailwayLine, RailwayBridge

bridges = RailwayBridge.query.all()

bridges_objects = []
for bridge in bridges:
    lines = RailwayLine.query.filter(
                geoalchemy2.func.ST_Intersects(RailwayLine.coordinates, bridge.geometry)
            ).all()

    bridge.rw_lines = lines
    bridges_objects.append(bridge)

db.session.add_all(bridges_objects)
db.session.commit()


