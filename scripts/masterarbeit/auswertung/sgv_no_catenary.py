import sqlalchemy

from prosd.models import TimetableTrainGroup, TimetableCategory, TimetableTrain, TimetableTrainPart, RailwayLine, MasterScenario, RouteTraingroup
from prosd.manage_db.version import Version
from prosd import db

scenario_id = 4
scenario = MasterScenario.query.get(scenario_id)
infra_version = Version(scenario=scenario)
rw_lines_no_catenary = infra_version.get_railwayline_no_catenary()


def running_km_no_catenary(transport_modes):
    rw_lines = db.session.query(RailwayLine.id, RailwayLine.length / 1000, sqlalchemy.func.count(TimetableTrain.id),
                                RailwayLine.length / 1000 * sqlalchemy.func.count(TimetableTrain.id)).join(
        RouteTraingroup,
        RouteTraingroup.railway_line_id == RailwayLine.id).join(
        TimetableTrainGroup, TimetableTrainGroup.id == RouteTraingroup.traingroup_id).join(TimetableTrain).join(
        TimetableTrainPart).join(TimetableCategory).filter(
        RouteTraingroup.master_scenario_id == scenario_id,
        TimetableCategory.transport_mode.in_(transport_modes),
        RailwayLine.id.in_(rw_lines_no_catenary)
    ).group_by(RailwayLine).all()

    infra_km = [line[1] for line in rw_lines]
    sum_infra_km = sum(infra_km)

    running_km = [line[3] for line in rw_lines]
    sum_running_km = sum(running_km)/1000

    return sum_infra_km, sum_running_km


def running_km_all(transport_modes):
    rw_lines = db.session.query(RailwayLine.id, RailwayLine.length/1000, sqlalchemy.func.count(TimetableTrain.id),
                                RailwayLine.length/1000 * sqlalchemy.func.count(TimetableTrain.id)).join(RouteTraingroup,
                                                                                                    RouteTraingroup.railway_line_id == RailwayLine.id).join(
        TimetableTrainGroup, TimetableTrainGroup.id == RouteTraingroup.traingroup_id).join(TimetableTrain).join(
        TimetableTrainPart).join(TimetableCategory).filter(
        RouteTraingroup.master_scenario_id == scenario_id,
        TimetableCategory.transport_mode.in_(transport_modes)
    ).group_by(RailwayLine).all()

    infra_km = [line[1] for line in rw_lines]
    sum_infra_km = sum(infra_km)

    running_km = [line[3] for line in rw_lines]
    sum_running_km = sum(running_km)/1000

    return sum_infra_km, sum_running_km


if __name__ == '__main__':
    infra_km_sgv_all, running_km_sgv_all = running_km_all(transport_modes = ['sgv'])
    infra_km_sgv_no_catenary, running_km_sgv_no_catenary = running_km_no_catenary(transport_modes = ['sgv'])

    infra_km_spfv_all, running_km_spfv_all = running_km_all(transport_modes=['spfv'])
    infra_km_spfv_no_catenary, running_km_spfv_no_catenary = running_km_no_catenary(transport_modes=['spfv'])

    infra_km_spnv_all, running_km_spnv_all = running_km_all(transport_modes=['spnv'])
    infra_km_spnv_no_catenary, running_km_spnv_no_catenary = running_km_no_catenary(transport_modes=['spnv'])

    infra_km_all, running_km_all = running_km_all(transport_modes=['sgv', 'spfv', 'spnv'])
    infra_km_no_catenary, running_km_no_catenary = running_km_no_catenary(transport_modes=['sgv', 'spfv', 'spnv'])


    print(infra_km_all)