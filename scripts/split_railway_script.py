from prosd import models
from prosd.graph import railgraph

def split_railway_line_by_station(railline_id, station_id):
    rg = railgraph.RailGraph()
    blade_point = models.RailwayPoint.query.get(station_id).coordinates
    rg._split_railway_lines(old_line_id=railline_id, blade_point=blade_point)


railline_id = 32635
station_id = 46253
split_railway_line_by_station(railline_id, station_id)


# TODO: Write a function to create project_content
    # read some fields through excel
    # create a fitting project (or a existing project)
    # projectcontent to constituencies, counties, states (intersect)
    # projectcontent to lines

