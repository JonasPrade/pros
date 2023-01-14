import logging

from prosd import db
from prosd.models import TimetableTrainGroup, RouteTraingroup, RailwayLine, TimetableTrainCost, TimetableLine
from prosd import parameter
from prosd.calculation_methods import use

# train_group_code = "SA3_X 3001 E 3"
# train_group = TimetableTrainGroup.query.filter(TimetableTrainGroup.code == train_group_code).one()

start_year = parameter.START_YEAR
duration_operation = parameter.DURATION_OPERATION

trainline_id = 1279
trainline = TimetableLine.query.get(trainline_id)

cost = use.StandiSpnv(
    trainline=trainline,
    traction='electrification',
    start_year_operation=2030,
    duration_operation=30
)
print(cost)
