from prosd.models import Formation
import datetime
import logging

formation = Formation.query.get("fo_1")
print(formation.maintenance_cost_km)
print(formation.weight)
print(formation.energy_stop_a)
print(formation.energy_stop_b)
print(formation.additional_energy_without_overhead)
print(formation.additional_maintenance_cost_without_overhead)
print(formation.energy_per_km)
print(formation.seats)
