from prosd.models import TimetableTrainGroup

code = "FR90 F 90201§"

tg = TimetableTrainGroup.query.filter(TimetableTrainGroup.code==code).one()

print(tg.id)
print(tg.code)
print(tg.stops)
print(tg)
