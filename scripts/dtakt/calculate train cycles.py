import datetime
import sqlalchemy

from prosd import db

from prosd.models import TimetableLine, TimetableTrain, TimetableTrainPart, TimetableOcp, TimetableTime, RailMlOcp


def get_earliest_departure(list_all_trains):
    """
    searches for the train with the earliest departure at their first stop
    :param list_all_trains:
    :return:
    """
    trains = dict()
    for train in list_all_trains:
        trains[train.train_part.first_ocp_departure] = train

    earliest_time = min(trains)
    earliest_train = trains[earliest_time]

    return earliest_train


def get_next_train(previous_train, list_all_trains, wait_time=datetime.timedelta(minutes=5)):
    # TODO: Add minimum wait time
    next_train = None
    time_information = None

    # get the ocp where the trains end
    ocp = previous_train.train_part.last_ocp.ocp
    arrival = previous_train.train_part.last_ocp_arrival

    # search all trains that starts here
    possible_trains = dict()
    for train in list_all_trains:
        if train.train_part.first_ocp.ocp == ocp:
            train_departure = train.train_part.first_ocp_departure
            delta_time = train_departure - arrival
            if delta_time > datetime.timedelta(0):
                possible_trains[delta_time] = train

    if possible_trains:
        next_train_time_delta = min(possible_trains)
        next_train = possible_trains[next_train_time_delta]
        time_information = next_train_time_delta

    return next_train, time_information


tt_line_id = 1605
line = TimetableLine.query.get(tt_line_id)

# create list with all tt_trains (list_all_trains)
list_all_trains = []
for tg in line.train_groups:
    for train in tg.trains:
        list_all_trains.append(train)

train_cycles_all = []
while len(list_all_trains) > 0:

    first_train = get_earliest_departure(list_all_trains)
    list_all_trains.remove(first_train)
    train_cycle = [first_train]
    turning_information = []

    previous_train = first_train
    while True:
        next_train, time_information = get_next_train(previous_train=previous_train, list_all_trains=list_all_trains)
        if next_train is None:
            train_cycles_all.append(train_cycle)
            break
        else:
            list_all_trains.remove(next_train)
            train_cycle.append(next_train)
            turning_information.append([previous_train.train_part.last_ocp.ocp, previous_train, previous_train.train_part.last_ocp_arrival, time_information, next_train.train_part.first_ocp_departure, next_train])
            previous_train = next_train

print(len(train_cycles_all))
