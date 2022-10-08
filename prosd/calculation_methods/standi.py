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
        additional_battery = vehicle.vehicle_pattern.additional_energy_without_overhead * self.tg.running_km_year_no_catenary
        energy_per_km = vehicle.vehicle_pattern.energy_per_km

        energy_running = (1 + additional_battery) * energy_per_km * self.tg.running_km_year

        energy_stops = 0
        #TODO Berechnungsblatt 2-4 weiter (energy stops)

        energy = energy_running + energy_stops

        return energy


if __name__ == "__main__":
    traingroup_id = "tg_SA3_X_x0020_3001_75905"
    st = Standi(traingroup_id=traingroup_id)
    st.energy_cost(vehicle=st.vehicles[0])
