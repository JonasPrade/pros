import sqlalchemy

from prosd import db
from prosd.manage_db.version import Version
from prosd.models import MasterScenario, MasterArea, TimetableTrainGroup, TimetableTrain, TimetableTrainPart, RouteTraingroup, TimetableCategory, RailwayLine

# calculate the areas
scenario_id = 2
scenario = MasterScenario.query.get(scenario_id)
scenario_infra = Version(scenario=scenario)
railwayline_no_catenary = scenario_infra.get_railwayline_no_catenary()

sgv_lines = db.session.query(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(RouteTraingroup).join(TimetableCategory).join(RailwayLine).filter(
    sqlalchemy.and_(
    RailwayLine.id.in_(railwayline_no_catenary),
    TimetableCategory.transport_mode == 'sgv'
)).all()

# TODO: Need system to remove all used traingroups
# TODO: Have to use a version of lines, not the lines itself!

# a list that contains the collected traingroups
area_objects = []

while sgv_lines:
    # take the first sgv_traingroup of the list and remove it from the list. Get also the railway_lines of that traingroup
    traingroups = list()
    rw_lines = list()
    sgv_line = sgv_lines.pop(0)
    traingroups.append(sgv_line)

    # if sgv_line.id in whitelist:
    #     continue

    length_rl_lines = sum(int(r.length) for r in rw_lines)

    # search for all lines that share a unelectrified railway_line witht the sgv_line
    delta_traingroups = True
    while delta_traingroups is True:
        rl_lines_additional = db.session.query(RailwayLine).join(RouteTraingroup).join(TimetableTrainGroup).filter(
            sqlalchemy.and_(
                RailwayLine.id.in_(railwayline_no_catenary),
                TimetableTrainGroup.id.in_([t.id for t in traingroups]),
                RailwayLine.id.notin_([r.id for r in rw_lines])
            )).all()

        if rl_lines_additional:
            rw_lines = rw_lines + rl_lines_additional

        traingroups_additional = db.session.query(TimetableTrainGroup).join(RouteTraingroup).join(RailwayLine).filter(
        sqlalchemy.and_(
            RailwayLine.id.in_(railwayline_no_catenary),
            RailwayLine.id.in_([r.id for r in rw_lines]),
            TimetableTrainGroup.id.notin_([t.id for t in traingroups])
    )).all()

        if traingroups_additional:
            traingroups = traingroups + traingroups_additional
        else:
            delta_traingroups = False

    # Remove used sgv lines from the sgv_lines
    for tg in traingroups:
        if tg.category.transport_mode == 'sgv' and tg is not sgv_line:
            sgv_lines.remove(tg)

    # add the traingroups as a collected group to the traingroup_cluster
    area = MasterArea()
    area.scenario_id = scenario_id
    area.traingroups = traingroups
    area.railway_lines = rw_lines
    area_objects.append(area)

    # traingroup_clusters[str(len(traingroup_clusters)+1)] = {"traingroups": traingroups, "railway_lines": rw_lines}

db.session.add_all(area_objects)
db.session.commit()