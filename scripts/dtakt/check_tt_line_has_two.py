# checks if all timetable_lines have two timetable_lines
import logging

from prosd.models import TimetableLine
from prosd import db

tt_lines = TimetableLine.query.all()

lines_problem = list()
for line in tt_lines:
    if len(line.train_groups)!=2:
        lines_problem.append(line)

logging.error(lines_problem)

