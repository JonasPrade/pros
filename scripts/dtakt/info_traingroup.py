from prosd.models import TimetableTrainGroup

code = "FR2 H 2001"

tg = TimetableTrainGroup.query.filter(TimetableTrainGroup.code==code).one()

vehicle = tg.vehicles[0]

for formation in vehicle.formations:
    print(formation)

print(tg.id)
print(tg.code)
print(tg.stops)
print(tg)
