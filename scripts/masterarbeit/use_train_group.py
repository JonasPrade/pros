import logging

from prosd import db
from prosd.models import TimetableTrainGroup, RouteTraingroup, RailwayLine, TimetableTrainCost
from prosd import parameter

# train_group_code = "SA3_X 3001 E 3"
# train_group = TimetableTrainGroup.query.filter(TimetableTrainGroup.code == train_group_code).one()

start_year = parameter.START_YEAR
duration_operation = parameter.DURATION_OPERATION

if __name__ == "__main__":
    traingroups = TimetableTrainGroup.query.join(RouteTraingroup).join(RailwayLine).filter(RailwayLine.catenary==False).all()
    tractions = ["electrification", "efuel", "battery", "h2", "diesel"]
    for tg in traingroups:
        cost = dict()
        for traction in tractions:
            if tg.category == 'spfv' and (traction == 'h2' or 'battery'):
                continue
            tt_cost = TimetableTrainCost.query.filter(
                TimetableTrainCost.traingroup_id == tg.id,
                TimetableTrainCost.master_scenario_id == 1,
                TimetableTrainCost.traction == traction
            )
            timetable_train_cost = TimetableTrainCost.create(
                traingroup=tg,
                master_scenario_id=1,
                traction=traction
            )
