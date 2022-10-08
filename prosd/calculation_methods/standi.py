from prosd.calculation_methods.base import BaseCalculation
from prosd.models import TimetableTrainGroup


class Standi:
    def __init__(self, traingroup_id, vehicles=None):
        if vehicles is None:
            vehicles = []

        self.tg = TimetableTrainGroup.query.get(traingroup_id)
        if not vehicles:
            self.vehicles = self.tg.trains[0].train_part.formation.vehicles

    def energy_cost(self, vehicle):
        additional_battery = vehicle.vehicle_pattern.additional_energy_without_overhead * self.tg.running_km_year_without_overhead
        energy_per_km = vehicle.vehicle_pattern.energy_per_km

        energy_running = (1 + additional_battery) * energy_per_km * self.tg.running_km_year

        energy_stops = 0

        energy = energy_running + energy_stops

