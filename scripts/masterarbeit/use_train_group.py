import logging

from prosd import db
from prosd.models import TimetableTrainGroup, RouteTraingroup, RailwayLine, TimetableTrainCost, TimetableLine
from prosd import parameter
from prosd.calculation_methods import use

# train_group_code = "SA3_X 3001 E 3"
# train_group = TimetableTrainGroup.query.filter(TimetableTrainGroup.code == train_group_code).one()

start_year = parameter.START_YEAR
duration_operation = parameter.DURATION_OPERATION

trainline_id = 1835
trainline = TimetableLine.query.get(trainline_id)

traingroup_id = 'tg_SH_AS_x0020_09903_132927'
traingroup = TimetableTrainGroup.query.get(traingroup_id)
print(traingroup.category.transport_mode)

cost = use.BvwpSgv(
    tg=traingroup,
    traction='electrification',
    start_year_operation=2030,
    duration_operation=30
)
print(cost.energy_cost_base_year)
