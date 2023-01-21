import pandas
from prosd import db
from prosd.models import RailwayLine, ProjectContent

filename = '../../example_data/import/pc_to_rwlines/template_pc_to_rwlines.xlsx'
df = pandas.read_excel(filename)

objects = []
for index, row in df.iterrows():
    pc = ProjectContent.query.get(int(row.pc))
    rw_lines = RailwayLine.query.get(int(row.rw_lines))
    pc.railway_lines.append(rw_lines)
    objects.append(pc)

db.session.add_all(objects)
db.session.commit()
