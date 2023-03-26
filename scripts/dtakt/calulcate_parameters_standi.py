import pandas
from prosd.models import TimetableTrainGroup, VehiclePattern
from prosd import db


# tg_id = "tg_NI7.a2_X_x0020_7302_18711"
# tg = TimetableTrainGroup.query.get(tg_id)

VEHICLE_RESERVE = 0.1
ANNUITY_FACTOR = 0.0428
PERSONAL_COST = 46

# # Berechnungsblatt 1-1 Fahrzeugtypen
# vehicles = tg.vehicles
# for vehicle in vehicles:
#     vp = vehicle.vehicle_pattern
#     seats = vp.vehicle_pattern.seat
#     if vp.project_group == 3:
#         investment_cost = vp.investment_cost_standi
#     else:
#         investment_cost = vp.investment_cost
#
#     weight = vp.weight
#     if vp.debt_service is None:
#         debt_service = investment_cost * ANNUITY_FACTOR
#
#     maintenance_cost_time = vp.maintenance_cost_duration_t*weight
#     maintenance_cost_km = vp.maintenance_cost_length_t*weight*(1/1000)
#     energy_cost_per_km = vp.energy_per_tkm*weight
#     thg_emission_production = vp.emission_production_vehicle*weight*(1/1000)


def calculate_debt_service():
    vehicles = VehiclePattern.query.filter(VehiclePattern.project_group == 3).all()
    updates = []
    for vehicle in vehicles:
        vehicle.debt_service = round(vehicle.investment_cost * ANNUITY_FACTOR * 1000, 3)
        updates.append(vehicle)

    db.session.bulk_save_objects(updates)
    db.session.commit()


def calculate_maintenance_duration():
    vehicles = VehiclePattern.query.filter(VehiclePattern.project_group == 3).all()
    updates = []
    for vehicle in vehicles:
        if vehicle.maintenance_cost_duration_t:
            vehicle.maintenance_cost_year = round(vehicle.maintenance_cost_duration_t * vehicle.weight, 3)
            updates.append(vehicle)

    db.session.bulk_save_objects(updates)
    db.session.commit()


def calculate_maintenance_km():
    vehicles = VehiclePattern.query.filter(VehiclePattern.project_group == 3).all()
    updates = []
    for vehicle in vehicles:
        if vehicle.maintenance_cost_length_t:
            vehicle.maintenance_cost_km = round(vehicle.maintenance_cost_length_t * vehicle.weight/1000, 3)
            updates.append(vehicle)

    db.session.bulk_save_objects(updates)
    db.session.commit()


def energy_per_km():
    vehicles = VehiclePattern.query.filter(VehiclePattern.project_group == 3).all()
    updates = []
    for vehicle in vehicles:
        if vehicle.energy_per_tkm:
            vehicle.energy_per_km = round(vehicle.energy_per_tkm * vehicle.weight / 1000, 3)
            updates.append(vehicle)

    db.session.bulk_save_objects(updates)
    db.session.commit()


def emission_production():
    vehicles = VehiclePattern.query.filter(VehiclePattern.project_group == 3).all()
    updates = []
    for vehicle in vehicles:
        if vehicle.emission_production_vehicle:
            vehicle.emission_production_vehicle_calc = round(vehicle.emission_production_vehicle * vehicle.weight / 1000, 3)
            updates.append(vehicle)

    db.session.bulk_save_objects(updates)
    db.session.commit()


energy_per_km()
