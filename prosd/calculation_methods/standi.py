import math

from prosd.calculation_methods.base import BaseCalculation
from prosd.models import TimetableTrainGroup


class Standi:
    def __init__(self, traingroup_id, vehicles=None):
        if vehicles is None:
            vehicles = []

        self.tg = TimetableTrainGroup.query.get(traingroup_id)
        if not vehicles:
            self.vehicles = self.tg.trains[0].train_part.formation.vehicles

    def energy(self, vehicle):
        additional_battery = vehicle.vehicle_pattern.additional_energy_without_overhead * self.tg.running_km_year_no_catenary
        energy_per_km = vehicle.vehicle_pattern.energy_per_km

        energy_running = (1 + additional_battery) * energy_per_km * self.tg.running_km_year

        # calculate energy usage through stops
        intermediate_1 = 55.6 * (self.tg.travel_time.total_seconds()/60 - self.tg.stops_duration.total_seconds()/60)
        segments = self.tg.stops_count - 1
        reference_speed = 3.6/(vehicle.vehicle_pattern.energy_stop_a * segments) * (intermediate_1 - math.sqrt(intermediate_1**2 - 2*vehicle.vehicle_pattern.energy_stop_a * segments * (self.tg.length_line*1000)))
        energy_per_stop = vehicle.vehicle_pattern.energy_stop_b * (reference_speed ** 2) * vehicle.vehicle_pattern.weight * (10**(-6))
        energy_stops = energy_per_stop * (self.tg.stops_count_year/1000)
        energy = energy_running + energy_stops

        return energy


if __name__ == "__main__":
    traingroup_id = "tg_NW19.1_N_x0020_19102_186"
    st = Standi(traingroup_id=traingroup_id)
    energy = st.energy(vehicle=st.vehicles[0])
    print(energy)
