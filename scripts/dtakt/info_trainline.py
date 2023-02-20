from prosd.models import TimetableLine

code = 'BW84.b_X'

line = TimetableLine.query.filter(TimetableLine.code == code).scalar()

train_cycles_all = line.get_train_cycles()
print(train_cycles_all)