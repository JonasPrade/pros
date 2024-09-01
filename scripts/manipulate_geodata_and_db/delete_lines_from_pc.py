from prosd.models import ProjectContent
from prosd import db

# delete all lines from project content
pc_id = 95926

pc = ProjectContent.query.get(pc_id)

pc.railway_lines = []
pc.generate_geojson()
pc.compute_centroid()

db.session.commit()
