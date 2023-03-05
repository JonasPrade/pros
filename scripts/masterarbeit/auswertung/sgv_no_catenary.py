from prosd.models import TimetableTrainGroup, TimetableCategory, TimetableTrain, TimetableTrainPart, RailwayLine, MasterScenario, RouteTraingroup
from prosd.manage_db.version import Version
from prosd import db

scenario_id = 4
scenario = MasterScenario.query.get(scenario_id)
infra_version = Version(scenario=scenario)
rw_lines_no_catenary = infra_version.get_railwayline_no_catenary()

sgv_lines = db.session.query(TimetableTrainGroup).join(TimetableTrain).join(TimetableTrainPart).join(TimetableCategory).join(RouteTraingroup).join(RailwayLine).filter(
    TimetableCategory.transport_mode == 'sgv',
    RouteTraingroup.master_scenario_id == scenario_id,
    RailwayLine.id.in_(rw_lines_no_catenary)
).group_by(TimetableTrainGroup.id).all()

running_km = [sgv.running_km_day(scenario_id) for sgv in sgv_lines]
sum_running_km = sum(running_km)


