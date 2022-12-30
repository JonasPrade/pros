import pandas

from prosd import db
from prosd.models import TimetableTrainGroup

filepath = '../../example_data/import/formations/add_missing_formations.csv'

file = pandas.read_csv(filepath_or_buffer=filepath, header=None, names=['traingroup', 'formation'])

objects = []
for index, row in file.iterrows():
    tg_id = row["traingroup"]
    traingroup = TimetableTrainGroup.query.get(tg_id)
    for train in traingroup.trains:
        train.train_part.formation_id = row["formation"]
        objects.append(train)

db.session.add_all(objects)
db.session.commit()
