import logging

from prosd import db
from prosd.models import TimetableTrainGroup, RouteTraingroup, RailwayLine
from prosd.calculation_methods.use import BvwpSgv, BvwpSpfv, BvwpSpnv, StandiSpnv, NoVehiclePatternExistsError, NoTractionFoundError

# train_group_code = "SA3_X 3001 E 3"
# train_group = TimetableTrainGroup.query.filter(TimetableTrainGroup.code == train_group_code).one()

start_year = 2030
duration_operation = 30

if __name__ == "__main__":
    traingroups = TimetableTrainGroup.query.join(RouteTraingroup).join(RailwayLine).filter(RailwayLine.catenary==False).all()
    tractions = ["electrification", "efuel", "battery", "h2", "diesel"]
    for tg in traingroups:
        cost = dict()
        for traction in tractions:
            try:
                match tg.category.transport_mode:
                    case "sgv":
                        if traction in ["battery", "h2"]:
                            train_cost = 0
                        else:
                            train_cost = BvwpSgv(tg_id=tg.id, start_year_operation=start_year,
                                                 duration_operation=duration_operation, traction=traction)
                            train_cost = train_cost.use
                    case "spfv":
                        if traction == "efuel":
                            # in this case, bvwp does not provide any vehicles
                            trainline = tg.traingroup_lines
                            train_cost = StandiSpnv(trainline_id=trainline.id, start_year_operation=start_year,
                                                    duration_operation=duration_operation, traction=traction)
                            train_cost = train_cost.use/len(trainline.train_groups)  # spread the cost to the traingroups
                        else:
                            train_cost = BvwpSpfv(tg_id=tg.id, start_year_operation=start_year,
                                                  duration_operation=duration_operation, traction=traction)
                            train_cost = train_cost.use
                    case "spnv":
                        # get the trainline and add all train_groups of that line to the whitelist
                        trainline = tg.traingroup_lines
                        train_cost = StandiSpnv(trainline_id=trainline.id, start_year_operation=start_year,
                                                duration_operation=duration_operation, traction=traction)
                        train_cost = train_cost.use / len(trainline.train_groups)  # spread the cost to the traingroups

                cost[traction] = train_cost
            except NoVehiclePatternExistsError as e:
                logging.error(f"For {tg} no train cost calculation possible {e} - {tg.trains[0].train_part.formation}")
                cost[traction] = None

        tg.cost_electro_renew = cost["electrification"]
        tg.cost_battery = cost["battery"]
        tg.cost_h2 = cost["h2"]
        cost_diesel = cost["diesel"]
        cost_efuel = cost["efuel"]

        db.session.add_all(traingroups)
        db.session.commit()
