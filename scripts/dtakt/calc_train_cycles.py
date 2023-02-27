import datetime
import logging

from prosd.models import TimetableLine, TrainCycle

"""
Calculates the count of needed formations for all TimetableLines
"""
logging.basicConfig(encoding='utf-8', level=logging.INFO)
tt_lines = TimetableLine.query.all()

objects = []
for index, line in enumerate(tt_lines):
    TrainCycle.get_train_cycles(
        timetableline_id=line.id,
        wait_time=datetime.timedelta(minutes=15)
    )


