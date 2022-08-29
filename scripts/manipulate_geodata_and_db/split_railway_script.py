from prosd import models
from prosd.graph import railgraph

def split_railway_line_by_station(railline_id, point_id):
    blade_point = models.RailwayNodes.query.get(point_id).coordinate
    # blade_point = models.RailwayPoint.query.get(point_id).coordinates
    models.RailwayLine.split_railwayline(old_line_id=railline_id, blade_point=blade_point)


railline_id = 16180
point_id = 78791
split_railway_line_by_station(railline_id, point_id)


# TODO: Write a function to create project_content
    # read some fields through excel
    # create a fitting project (or a existing project)
    # projectcontent to constituencies, counties, states (intersect)
    # projectcontent to lines

