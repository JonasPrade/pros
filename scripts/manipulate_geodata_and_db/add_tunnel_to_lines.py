import geopandas
import geoalchemy2

from prosd import db
from prosd.models import RailwayLine, RailwayTunnel

tunnels = RailwayTunnel.query.all()

tunnel_objects = []
for tunnel in tunnels:
    lines = RailwayLine.query.filter(
                geoalchemy2.func.ST_Intersects(RailwayLine.coordinates, tunnel.geometry)
            ).all()

    tunnel.rw_lines = lines
    tunnel_objects.append(tunnel)

db.session.add_all(tunnel_objects)
db.session.commit()


