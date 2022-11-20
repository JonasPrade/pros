import geopandas
import geoalchemy2

from prosd import db
from prosd.models import RailwayLine, RailwayTunnel

tunnels = RailwayTunnel.query.all()

line_objects = []
for tunnel in tunnels:
    lines = RailwayLine.query.filter(
                geoalchemy2.func.ST_Intersects(RailwayLine.coordinates, tunnel.geometry)
            ).all()

    for line in lines:
        line.tunnel_id = tunnel.id
        line_objects.append(line)

db.session.add_all(line_objects)
db.session.commit()


