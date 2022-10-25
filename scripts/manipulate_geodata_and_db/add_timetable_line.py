import logging

from prosd.models import TimetableLine, TimetableTrainGroup
from prosd import db

tgs = TimetableTrainGroup.query.all()

objects = []
for tg in tgs:
    if tg.category.transport_mode != "sgv" and tg.traingroup_line is None:
        line_id = tg.code.split(str(tg.train_number))[0].strip()
        line = TimetableLine.query.filter(TimetableLine.code == line_id).scalar()
        if line is None:
            tt_line = TimetableLine(
                code=line_id
            )
            db.session.add(tt_line)
            db.session.commit()
        else:
            if len(line.train_groups) >= 2:
                logging.error( f"Line {line} has already two traingroups {line.train_groups}. Additional traingroup is not added {tg}")
                continue

        tg.traingroup_line = line_id
        db.session.add(tg)
        db.session.commit()




