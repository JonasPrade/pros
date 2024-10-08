from prosd import db
from prosd.postgisbasics import PostgisBasics
from prosd.models import RailwayLine

lines_update = RailwayLine.query.all()

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
