import logging
import math
import os

from prosd.models import TimetableTrainGroup, VehiclePattern, TimetableLine
from prosd.calculation_methods.base import BaseCalculation


class NoTractionFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoTransportmodeFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class BvwpUse:
    def __init__(self, traingroup_id, traction, transport_mode, vehicles=None):
        self.transport_mode = transport_mode

        if vehicles is None:
            self.vehicles = []
        else:
            self.vehicles = vehicles

        self.traction = traction

        self.ENERGY_COST_ELECTRO = 0.1536
        self.ENERGY_COST_DIESEL = 0.74

        self.tg = TimetableTrainGroup.query.get(traingroup_id)
        if not self.vehicles:
            self.vehicles = self.tg.trains[0].train_part.formation.vehicles

    def debt_service(self, vehicle_pattern):
        debt_service = vehicle_pattern.debt_service * self.tg.running_time_year
        return debt_service

    def maintenance_cost(self, vehicle_pattern):
        maintenance_cost = vehicle_pattern.maintenance_cost_km * self.tg.running_km_year
        return maintenance_cost

    def energy_cost(self, vehicle_pattern):
        if vehicle_pattern.type_of_traction == "Elektro":
            energy = self.energy_electro(vehicle_pattern)
            energy_cost = self.ENERGY_COST_ELECTRO * energy
        elif vehicle_pattern.type_of_traction == "Diesel":
            energy = self.energy_diesel(vehicle_pattern)
            energy_cost = self.ENERGY_COST_DIESEL * energy
        else:
            energy_cost = 0
            logging.error("No fitting traction found")
        return energy_cost

    def energy_electro(self, vehicle_pattern):
        energy = vehicle_pattern.energy_per_km * self.tg.running_km_year
        return energy

    def energy_diesel(self, vehicle_pattern):
        energy = vehicle_pattern.fuel_consumption_diesel_km * self.tg.running_km_year
        return energy

    def calc_use(self, vehicles_list):
        use = 0
        debt_service_sum = 0
        maintenance_cost_sum = 0
        energy_cost_sum = 0
        for vehicle in vehicles_list:
            vehicle_pattern = self._vehicle_pattern_by_traction(vehicle)
            debt_service = self.debt_service(vehicle_pattern)
            maintenance_cost = self.maintenance_cost(vehicle_pattern)
            energy_cost = self.energy_cost(vehicle_pattern)

            debt_service_sum += debt_service
            maintenance_cost_sum += maintenance_cost
            energy_cost_sum += energy_cost
            use += debt_service + maintenance_cost + energy_cost

        return use, debt_service_sum, maintenance_cost_sum, energy_cost_sum

    def _vehicle_pattern_by_traction(self, vehicle):
        """

        :return:
        """
        vehicle_pattern_transportmode = self._vehicle_pattern_by_transport_mode(vehicle)

        match self.traction:
            case "electrification":
                vehicle_pattern_id = vehicle_pattern_transportmode.vehicle_pattern_id_electrical
            case "h2":
                vehicle_pattern_id = vehicle_pattern_transportmode.vehicle_pattern_id_h2
            case "battery":
                vehicle_pattern_id = vehicle_pattern_transportmode.vehicle_pattern_id_battery
            case "efuel":
                vehicle_pattern_id = vehicle_pattern_transportmode.vehicle_pattern_id_efuel
            case _:
                raise NoTractionFoundError(message=f"Traction {self.traction} is not a valid case")

        #TODO: Check if vehicle_pattern exists. If not throw an - to be created - exception
        vehicle_pattern = VehiclePattern.query.get(vehicle_pattern_id)

        return vehicle_pattern

    def _vehicle_pattern_by_transport_mode(self, vehicle):
        """

        :param vehicle:
        :return:
        """
        match self.transport_mode:
            case 'spfv':
                vehicle_pattern_id_transportmode = vehicle.vehicle_pattern_spfv
            case 'spnv':
                vehicle_pattern_id_transportmode = vehicle.vehicle_pattern_spnv
            case 'sgv':
                vehicle_pattern_id_transportmode = vehicle.vehicle_pattern_sgv
            case _:
                raise NoTransportmodeFoundError(message=f"There is no transportmode called {self.transport_mode}")

        vehicle_pattern_transportmode = VehiclePattern.query.get(vehicle_pattern_id_transportmode)

        return vehicle_pattern_transportmode


class BvwpSgv(BvwpUse):
    def __init__(self, tg_id, traction, vehicles=None):
        self.transport_mode = 'sgv'
        super().__init__(traingroup_id=tg_id, vehicles=vehicles, traction=traction, transport_mode='sgv')
        self.loko = self.vehicles[0]
        self.waggon = self.vehicles[1]

        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum = super().calc_use(vehicles_list=[self.loko])

    def energy_electro(self, vehicle_pattern):
        energy = 1.08 * (self.waggon.brutto_weight ** (-0.62)) * self.tg.running_km_year
        return energy

    def energy_diesel(self, vehicle_pattern):
        energy = 0.277 * (self.waggon.brutto_weight ** (-0.62)) * self.tg.running_km_year
        return energy


class BvwpSpfv(BvwpUse):
    def __init__(self, tg_id, traction, vehicles=None):
        self.transport_mode = 'spfv'
        super().__init__(traingroup_id=tg_id, vehicles=vehicles, traction=traction, transport_mode='spfv')

        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum = super().calc_use(vehicles_list=self.vehicles)

    def energy_electro(self, vehicle_pattern):
        energy_electro = self.energy(vehicle_pattern=vehicle_pattern)
        return energy_electro

    def energy(self, vehicle_pattern):
        running_km_year_ks = self.tg.running_km_year - self.tg.running_km_year_abs - self.tg.running_km_year_nbs
        energy_km_ks = running_km_year_ks * vehicle_pattern.energy_per_km
        energy_km_abs = self.tg.running_km_year_abs * vehicle_pattern.energy_abs_per_km
        energy_km_nbs = self.tg.running_km_year_nbs * vehicle_pattern.energy_nbs_per_km
        energy_km = energy_km_nbs + energy_km_abs + energy_km_ks

        energy_time = self.tg.running_time_year * vehicle_pattern.energy_consumption_hour

        energy = energy_km + energy_time
        return energy


class BvwpSpnv(BvwpUse):
    def __init__(self, tg_id, traction, vehicles=None):
        self.transport_mode = 'spnv'
        super().__init__(traingroup_id=tg_id, vehicles=vehicles, traction=traction, transport_mode='spnv')

        self.use = super().calc_use(vehicles_list=self.vehicles)

    def energy_electro(self, vehicle_pattern):
        energy_km = self.tg.running_km_year * vehicle_pattern.energy_per_km
        energy_time = self.tg.running_time_year * vehicle_pattern.energy_consumption_hour
        energy = energy_km + energy_time
        return energy

    # TODO: Is energy_diesel also need update??


class StandiSpnv(BvwpUse):
    def __init__(self, trainline_id, traction, vehicles=None):
        self.transport_mode = 'spnv'
        self.ENERGY_COST_ELECTRO = 0.1536
        self.ENERGY_COST_DIESEL = 0.74
        self.traction = traction

        # TODO: Make that compatible to different vehicle_patterns

        if vehicles is None:
            self.vehicles = []
        else:
            self.vehicles = vehicles

        self.trainline = TimetableLine.query.get(trainline_id)
        self.traingroups = self.trainline.train_groups

        if not self.vehicles:
            self.vehicles = self.traingroups[0].trains[0].train_part.formation.vehicles

        self.train_cycles = self.trainline.get_train_cycle()

        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum = self.calc_use()

    def calc_use(self):
        use = 0

        debt_service = self.debt_service()
        maintenance_cost_time = self.maintenance_cost_time()

        energy_cost_sum = 0
        maintenance_cost_running_sum = 0
        for tg in self.traingroups:
            vehicles = tg.trains[0].train_part.formation.vehicles
            for vehicle in vehicles:
                vehicle_pattern = super()._vehicle_pattern_by_traction(vehicle=vehicle)
                energy_cost = self.energy_cost(vehicle_pattern=vehicle_pattern, traingroup=tg)
                maintenance_cost_running = self.maintenance_cost_running(vehicle_pattern=vehicle_pattern, traingroup=tg)

                energy_cost_sum += energy_cost
                maintenance_cost_running_sum += maintenance_cost_running

        maintenance_cost_sum = maintenance_cost_time + maintenance_cost_running_sum
        use += debt_service
        use += maintenance_cost_time
        use += energy_cost_sum
        use += maintenance_cost_running_sum
        return use, debt_service, maintenance_cost_sum, energy_cost_sum

    def debt_service(self):
        debt_service_vehicles = 0
        for vehicle in self.vehicles:
            vehicle_pattern = super()._vehicle_pattern_by_traction(vehicle=vehicle)
            debt_service_vehicles += vehicle_pattern.debt_service

        count_formations = len(self.train_cycles)

        debt_service = count_formations * debt_service_vehicles

        return debt_service

    def maintenance_cost_running(self, vehicle_pattern, traingroup):
        additional_maintenance_battery = traingroup.running_km_year_no_catenary * vehicle_pattern.additional_maintenance_cost_withou_overhead
        maintenance_cost = (1 + additional_maintenance_battery) * vehicle_pattern.maintenance_cost_km * traingroup.running_km_year

        return maintenance_cost

    def maintenance_cost_time(self):
        maintenance_cost_time_vehicles = 0
        for vehicle in self.vehicles:
            vehicle_pattern = super()._vehicle_pattern_by_traction(vehicle=vehicle)
            maintenance_cost_time_vehicles += vehicle_pattern.maintenance_cost_duration_t * vehicle.vehicle_pattern.weight

        count_formations = len(self.train_cycles)

        maintenance_cost_time = count_formations * maintenance_cost_time_vehicles / 1000

        return maintenance_cost_time

    def energy_cost(self, vehicle_pattern, traingroup):
        if vehicle_pattern.type_of_traction == "Elektro":
            energy = self.energy(vehicle_pattern=vehicle_pattern, traingroup=traingroup)
            energy_cost = self.ENERGY_COST_ELECTRO * energy
        elif vehicle_pattern.type_of_traction == "Diesel":
            energy = self.energy(vehicle_pattern=vehicle_pattern, traingroup=traingroup)
            energy_cost = self.ENERGY_COST_DIESEL * energy
        else:
            energy_cost = 0
            logging.error("No fitting traction found")
        return energy_cost

    def energy(self, vehicle_pattern, traingroup):
        additional_battery = vehicle_pattern.additional_energy_without_overhead * traingroup.running_km_year_no_catenary
        energy_per_km = vehicle_pattern.energy_per_km

        energy_running = (1 + additional_battery) * energy_per_km * traingroup.running_km_year

        # calculate energy usage through stops
        intermediate_1 = 55.6 * (traingroup.travel_time.total_seconds()/60 - traingroup.stops_duration.total_seconds()/60)
        segments = traingroup.stops_count - 1
        try:
            reference_speed = 3.6/(vehicle_pattern.energy_stop_a * segments) * (intermediate_1 - math.sqrt(intermediate_1**2 - 2*vehicle_pattern.energy_stop_a * segments * (traingroup.length_line*1000)))
        except ValueError:
            logging.warning(f'Could not calculate reference speed for line {self.trainline}. More information on page 197 Verfahrensanleitung Standardisierte Bewertung')
            reference_speed = 160
        energy_per_stop = vehicle_pattern.energy_stop_b * (reference_speed ** 2) * vehicle_pattern.weight * (10**(-6))
        energy_stops = energy_per_stop * (traingroup.stops_count_year/1000)
        energy = energy_running + energy_stops

        return energy


if __name__ == "__main__":
    # tg_id = "tg_718_x0020_G_x0020_2503_120827"
    # sgv = BvwpSgv(tg_id, traction='electrification')
    # print(sgv.use)

    # tg_id = "tg_FV34.a_x0020_B_x0020_34001_128185"
    # spfv = BvwpSpfv(tg_id, traction='electrification')
    # print(spfv.use)

    # tg_id = "tg_NW19.1_N_x0020_19102_186"
    trainline_id = 1298
    #
    # vehicles = [Vehicle.query.get("ve_1049")]
    # spnv = BvwpSpnv(tg_id, vehicles=vehicles)
    # print(spnv.use)
    #
    # tg_id = "tg_NW19.1_N_x0020_19102_186"
    # vehicles = [Vehicle.query.get("ve_1049")]
    # spnv = BvwpSpnv(tg_id, vehicles=vehicles)
    # print(spnv.use)

    spnv = StandiSpnv(trainline_id, traction='electrification')
    print(spnv.use)


