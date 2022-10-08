import logging
import pandas
import os

from prosd.models import TimetableTrainGroup, VehiclePattern
from prosd.calculation_methods.base import BaseCalculation


class BvwpUse:
    def __init__(self, traingroup_id, vehicles=None):
        if vehicles is None:
            vehicles = []
        self.ENERGY_COST_ELECTRO = 0.1536
        self.ENERGY_COST_DIESEL = 0.74

        self.tg = TimetableTrainGroup.query.get(traingroup_id)
        if not vehicles:
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
        running_km_year_ks = self.tg.running_km_year - self.tg.running_km_year_abs - self.tg.running_km_year_nbs
        energy_km_ks = running_km_year_ks * vehicle.vehicle_pattern.energy_per_km
        energy_km_abs = self.tg.running_km_year_abs * vehicle.vehicle_pattern.energy_abs_per_km
        energy_km_nbs = self.tg.running_km_year_nbs * vehicle.vehicle_pattern.energy_nbs_per_km
        energy_km = energy_km_nbs + energy_km_abs + energy_km_ks
        energy_time = self.tg.running_km_year * vehicle.vehicle_pattern.energy_consumption_hour
        energy = energy_km + energy_time
        return energy


class BvwpSpnv(BvwpUse):
    def __init__(self, tg_id, vehicles=None):
        self.ENERGY_COST_ELECTRO = 0.156
        super().__init__(traingroup_id=tg_id, vehicles=vehicles)

        self.use = super().calc_use(vehicles_list=self.vehicles)

    def energy_electro(self, vehicle):
        energy_km = self.tg.running_km_year * vehicle.vehicle_pattern.energy_per_km
        energy_time = self.tg.running_km_year * vehicle.vehicle_pattern.energy_consumption_hour
        energy = energy_km + energy_time
        return energy

    # TODO: Is energy_diesel also need update??




# if __name__ == "__main__":
    # tg_id = "tg_718_x0020_G_x0020_2503_120827"
    # sgv = BvwpSgv(tg_id)
    # print(sgv.use)

    # tg_id = "tg_FV4.a_x0020_A_x0020_4101_134067"
    # spfv = BvwpSpfv(tg_id)
    # print(spfv.use)

    # tg_id = "tg_NW19.1_N_x0020_19102_186"
    # spnv = BvwpSpnv(tg_id)
    # print(spnv.use)


