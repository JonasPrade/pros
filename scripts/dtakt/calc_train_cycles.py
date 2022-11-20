import datetime
import logging

from prosd import db
from prosd.models import TimetableLine

"""
Calculates the count of needed formations for all TimetableLines
"""
logging.basicConfig(encoding='utf-8', level=logging.INFO)

RECALCULATE = True
FACTOR_WAIT_TIME = 0.05  # in relation to one way travel time

tt_lines = TimetableLine.query.all()

objects = []
for index, line in enumerate(tt_lines):
    if line.count_formations is None and RECALCULATE:
        travel_time = line.train_groups[0].travel_time
        wait_time = max(travel_time * FACTOR_WAIT_TIME, datetime.timedelta(minutes=5))
        count_formations = line.get_train_cycle(wait_time=wait_time)
        line.count_formations = len(count_formations)
        db.session.add(line)
        db.session.commit()
        logging.info(f"{index} of {len(tt_lines)} finished ({line})")


