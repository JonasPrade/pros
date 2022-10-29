import logging
import math
import os

from prosd.models import TimetableTrainGroup, Vehicle
from prosd.calculation_methods.base import BaseCalculation


class BvwpUse:
    def __init__(self, traingroup_id, vehicles=None):
        if vehicles is None:
            self.vehicles = []
        else:
            self.vehicles = vehicles

        self.ENERGY_COST_ELECTRO = 0.1536
        self.ENERGY_COST_DIESEL = 0.74

        self.tg = TimetableTrainGroup.query.get(traingroup_id)
        if not self.vehicles:
            self.vehicles = self.tg.trains[0].train_part.formation.vehicles

    def debt_service(self, vehicle):
        debt_service = vehicle.vehicle_pattern.debt_service * self.tg.running_time_year
        return debt_service

    def maintenance_cost(self, vehicle):
        maintenance_cost = vehicle.vehicle_pattern.maintenance_cost_km * self.tg.running_km_year
        return maintenance_cost

    def energy_cost(self, vehicle):
        if vehicle.vehicle_pattern.type_of_traction == "Elektro":
            energy = self.energy_electro(vehicle)
            energy_cost = self.ENERGY_COST_ELECTRO * energy
        elif vehicle.vehicle_pattern.type_of_traction == "Diesel":
            energy = self.energy_diesel(vehicle)
            energy_cost = self.ENERGY_COST_DIESEL * energy
        else:
            energy_cost = 0
            logging.error("No fitting traction found")
        return energy_cost

    def energy_electro(self, vehicle):
        energy = vehicle.vehicle_pattern.energy_per_km * self.tg.running_km_year
        return energy

    def energy_diesel(self, vehicle):
        energy = vehicle.vehicle_pattern.fuel_consumption_diesel_km * self.tg.running_km_year
        return energy

    def calc_use(self, vehicles_list):
        use = 0
        for vehicle in vehicles_list:
            debt_service = self.debt_service(vehicle)
            maintenance_cost = self.maintenance_cost(vehicle)
            energy_cost = self.energy_cost(vehicle)

            use += debt_service + maintenance_cost + energy_cost

        return use


class BvwpSgv(BvwpUse):
    def __init__(self, tg_id, vehicles=None):
        super().__init__(traingroup_id=tg_id, vehicles=vehicles)
        self.loko = self.vehicles[0]
        self.waggon = self.vehicles[1]

        self.use = super().calc_use(vehicles_list=[self.loko])

    def energy_electro(self, vehicle):
        energy = 1.08 * (self.waggon.brutto_weight ** (-0.62)) * self.tg.running_km_year
        return energy

    def energy_diesel(self, vehicle):
        energy = 0.277 * (self.waggon.brutto_weight ** (-0.62)) * self.tg.running_km_year
        return energy


class BvwpSpfv(BvwpUse):
    def __init__(self, tg_id, vehicles=None):
        super().__init__(traingroup_id=tg_id, vehicles=vehicles)

        self.use = super().calc_use(vehicles_list=self.vehicles)

    def energy_electro(self, vehicle):
        energy_electro = self.energy(vehicle=vehicle)
        return energy_electro

    def energy(self, vehicle):
        running_km_year_ks = self.tg.running_km_year - self.tg.running_km_year_abs - self.tg.running_km_year_nbs
        energy_km_ks = running_km_year_ks * vehicle.vehicle_pattern.energy_per_km
        energy_km_abs = self.tg.running_km_year_abs * vehicle.vehicle_pattern.energy_abs_per_km
        energy_km_nbs = self.tg.running_km_year_nbs * vehicle.vehicle_pattern.energy_nbs_per_km
        energy_km = energy_km_nbs + energy_km_abs + energy_km_ks

        energy_time = self.tg.running_time_year * vehicle.vehicle_pattern.energy_consumption_hour

        energy = energy_km + energy_time
        return energy


class BvwpSpnv(BvwpUse):
    def __init__(self, tg_id, vehicles=None):
        super().__init__(traingroup_id=tg_id, vehicles=vehicles)

        self.use = super().calc_use(vehicles_list=self.vehicles)

    def energy_electro(self, vehicle):
        energy_km = self.tg.running_km_year * vehicle.vehicle_pattern.energy_per_km
        energy_time = self.tg.running_time_year * vehicle.vehicle_pattern.energy_consumption_hour
        energy = energy_km + energy_time
        return energy

    # TODO: Is energy_diesel also need update??


class StandiSpnv(BvwpUse):
    def __init__(self, tg_id, vehicles=None):
        super().__init__(traingroup_id=tg_id, vehicles=vehicles)

        self.use = super().calc_use(vehicles_list=self.vehicles)

        # TODO: These: Das hier muss komplett anders angegangen werden.

    def calc_use(self):
        pass

    def debt_service(self):
        pass

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
    # tg_id = "tg_718_x0020_G_x0020_2503_120827"
    # sgv = BvwpSgv(tg_id)
    # print(sgv.use)

    # tg_id = "tg_FV4.a_x0020_A_x0020_4101_134067"
    # spfv = BvwpSpfv(tg_id)
    # print(spfv.use)

    tg_id = "tg_NW19.1_N_x0020_19102_186"
    vehicles = [Vehicle.query.get("ve_1049")]
    spnv = BvwpSpnv(tg_id, vehicles=vehicles)
    print(spnv.use)

    tg_id = "tg_NW19.1_N_x0020_19102_186"
    spnv = StandiSpnv(tg_id)
    print(spnv.use)


