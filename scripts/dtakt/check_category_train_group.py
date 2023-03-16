import logging

from prosd.models import TimetableTrainGroup

def check_traingroup_same_category(tgs):
    for tg in tgs:
        categories = set()
        for train in tg.trains:
            categories.add(train.train_part.category.id)

        if len(categories) != 1:
            logging.warning("TrainGroup " + str(tg.id) + " has this categories " + str(categories))


def check_traingroup_same_way(tgs):
    for tg in tgs:
        first_ocp_tg = set()
        last_ocp_tg = set()
        for train in tg.trains:
            first_ocp_tg.add(train.train_part.first_ocp.blocked_ocp.id)
            last_ocp_tg.add(train.train_part.last_ocp.blocked_ocp.id)

        if len(first_ocp_tg) != 1:
            logging.warning("TrainGroup " + str(tg.id) + " has multiple first_ocp " + str(first_ocp_tg))
        if len(last_ocp_tg) != 1:
            logging.warning("TrainGroup " + str(tg.id) + " has multiple last_ocp " + str(last_ocp_tg))


def check_traingroup_same_formation(tgs):
    for tg in tgs:
        formations = set()
        for train in tg.trains:
            formations.add(train.train_part.formation_id)
        if len(formations) !=1:
            logging.warning("TrainGroup has multiple formations " + str(tg.id) + " " + str(formations))

tgs = TimetableTrainGroup.query.all()
# check_traingroup_same_category(tgs)
# check_traingroup_same_way(tgs)
check_traingroup_same_formation(tgs)
