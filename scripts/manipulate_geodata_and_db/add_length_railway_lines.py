import geoalchemy2
import sqlalchemy.orm

from prosd import db
from prosd.postgisbasics import PostgisBasics
from prosd.models import RailwayLine, RailwayRoute

routes = RailwayRoute.query.all()

# # variant, if there was a problem with splitted RailwayLines
# lines_update = set()
#
# line_1 = sqlalchemy.orm.aliased(RailwayLine)
# line_2 = sqlalchemy.orm.aliased(RailwayLine)
#
# query = db.session.query(line_1, line_2).filter(line_1.mifcode == None, line_2.mifcode == None).outerjoin(
#     line_2, sqlalchemy.and_(
#         line_1.length == line_2.length,
#         line_1.id != line_2.id,
#         line_1.route_number == line_2.route_number,
#         line_1.from_km == line_2.from_km,
#         line_1.to_km == line_2.to_km
#     )
# ).all()
#
# for row in query:
#     for element in row:
#         if None:
#             continue
#         else:
#             lines_update.add(element)

lines_update = RailwayLine.query.filter(RailwayLine.length == None).all()

updated_lines = []
for line in lines_update:
    if line is None:
        continue
    pgis_basics = PostgisBasics(geometry=line.coordinates, srid=4326)
    length = round(pgis_basics.length_in_meter())
    line.length = length
    updated_lines.append(line)

db.session.bulk_save_objects(updated_lines)
db.session.commit()