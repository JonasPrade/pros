from prosd import db
from prosd.models import ProjectContent

pc_id = 95533
pc = ProjectContent.query.get(pc_id)
pc.projectcontent_groups = []
pc.texts = []
pc.railway_lines = []
pc.railway_stations = []

db.session.delete(pc)
db.session.commit()