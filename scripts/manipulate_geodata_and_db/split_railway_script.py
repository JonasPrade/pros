from prosd import models
from prosd.graph import railgraph

def split_railway_line_by_station(railline_id, point_id):
    blade_point = models.RailwayNodes.query.get(point_id).coordinate
    # blade_point = models.RailwayPoint.query.get(point_id).coordinates
    models.RailwayLine.split_railwayline(old_line_id=railline_id, blade_point=blade_point)


railline_id = 8076
point_id = 79304
split_railway_line_by_station(railline_id, point_id)


