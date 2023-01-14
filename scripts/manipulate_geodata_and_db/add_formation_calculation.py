from prosd import db
from prosd.models import Formation, Vehicle, VehiclePattern, formations_to_vehicles, TimetableTrainPart, TimetableCategory

formation_calculation_id = 'ref_fo_e_spfv_hgv_d_7'
vehicle_pattern_id = 70

formations = db.session.query(Formation)\
    .join(formations_to_vehicles).join(Vehicle).join(TimetableTrainPart).join(TimetableCategory)\
    .filter(Vehicle.vehicle_pattern_spnv_id == 70 and TimetableCategory.transport_mode==)\
    .all()

updates = []
formation_types = set()
for formation in formations:
    print(f"{len(formation.vehicles_composition)}")


formation_composition = Formation()
formation_composition.id = formation_calculation_id
formation_composition.description = 'Ersatz für HGV D 5 Standi'
formation_composition.length = 132
formation_composition.speed = 160
db.session.add(formation_composition)
db.session.commit()


updates = []
for formation in formations:
    print(len(formation.vehicles_composition))
    formation.formation_id_calculation_standi = formation_calculation_id
    updates.append(formation)

db.session.add_all(updates)
db.session.commit()
