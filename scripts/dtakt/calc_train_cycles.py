import datetime
import logging

from prosd import db
from prosd.models import TimetableLine, TrainCycle

"""
Calculates the count of needed formations for all TimetableLines
"""
logging.basicConfig(encoding='utf-8', level=logging.INFO)

RECALCULATE = True
FACTOR_WAIT_TIME = 0.05  # in relation to one way travel time

tt_lines = TimetableLine.query.all()

objects = []
for index, line in enumerate(tt_lines):
    TrainCycle.get_train_cycles(
        timetableline_id=line.id
    )


