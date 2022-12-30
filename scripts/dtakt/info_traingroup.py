from prosd import db
import sqlalchemy
from prosd.models import TimetableTrainGroup, TimetableTrain, Formation, TimetableTrainPart, TimetableLine

#
# list = db.session.query(TimetableLine).join(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).filter(
#     TimetableLine.code.like('%MV%')
# ).all()

# list = db.session.query(TimetableLine).join(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).filter(
#     sqlalchemy.and_(
#     TimetableTrainPart.formation_id.is_(None),
#     TimetableLine.code.like('%BB%')
# )).all()

# list = db.session.query(TimetableTrainPart).join(TimetableTrain).join(TimetableTrainGroup).join(TimetableLine).filter(
#     sqlalchemy.and_(
#     TimetableTrainPart.formation_id.is_(None),
#     TimetableLine.code.like('%BB%')
# )).all()

tg = TimetableTrainGroup.query.get("tg_116_x0020_G_x0020_2503_117841")

formation = Formation.query.get('fo_678')

# for train_part in list:
#     train_part.formation = formation
#
# db.session.add_all(list)
# db.session.commit()

print(list)
