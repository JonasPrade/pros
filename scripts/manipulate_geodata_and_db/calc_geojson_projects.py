from prosd.models import ProjectContent
from prosd import db
import logging

logging.basicConfig(level=logging.INFO)


def calc_update_geo_properties(id):
    if id == "all":
        pcs = ProjectContent.query.all()
    else:
        pcs = ProjectContent.query.filter_by(id=id)
    for pc in pcs:
        pc.update_geo_properties()
        logging.info(f"finished {pc.id}")
    db.session.add_all(pcs)
    db.session.commit()


if __name__ == '__main__':
    # namen an id or type all
    id = 95419
    calc_update_geo_properties(id)
