from prosd.models import ProjectContent
from prosd import db
import logging

logging.basicConfig(level=logging.INFO)


def calc_update_geo_properties():
    pcs = ProjectContent.query.all()
    for pc in pcs:
        pc.compute_centroid()
        logging.info(f"finished {pc.id}")
    db.session.add_all(pcs)
    db.session.commit()


if __name__ == '__main__':
    calc_update_geo_properties()