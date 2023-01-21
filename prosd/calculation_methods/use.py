import logging
import math

from prosd.calculation_methods.base import BaseCalculation
from prosd import parameter


class NoTractionFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoTransportmodeFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoVehiclePatternExistsError(Exception):
    def __init__(self, message):
        super().__init__(message)


def get_formation_calculation_bvwp(formation):
    if formation.formation_id_calculation_bvwp is None:
        formation_calculation = formation
    else:
        formation_calculation = formation.formation_calculation_bvwp

    return formation_calculation


def get_formation_calculation_standi(formation):
    if formation.formation_id_calculation_standi is None:
        formation_calculation = formation
    else:
        formation_calculation = formation.formation_calculation_standi

    return formation_calculation


class BvwpUse(BaseCalculation):
    def __init__(self, model, traction, transport_mode, formation, tg_or_tl='tg'):
        """

        :param id:
        :param traction:
        :param transport_mode:
        :param tg_or_tl:
        :param vehicles:
        """
        super().__init__()
        self.transport_mode = transport_mode

        self.traction = traction

        if tg_or_tl == 'tg':
            self.tg = model

        elif tg_or_tl == 'tl':
            self.trainline = model
            self.traingroups = self.trainline.train_groups

        self.vehicles = formation.vehicles_composition

        # TODO: Check if a vehicle has waggons

        self.ENERGY_COST_ELECTRO_CASUAL = parameter.ENERGY_COST_ELECTRO_CASUAL
        self.ENERGY_COST_ELECTRO_RENEWABLE = parameter.ENERGY_COST_ELECTRO_RENEWABLE
        self.ENERGY_COST_DIESEL = parameter.ENERGY_COST_DIESEL
        self.ENERGY_COST_EFUEL = parameter.ENERGY_COST_EFUEL
        self.ENERGY_COST_H2 = parameter.ENERGY_COST_H2

        self.ENERGY_CO2_ELECTRO_CASUAL = parameter.ENERGY_CO2_ELECTRO_CASUAL
        self.ENERGY_CO2_ELECTRO_RENEWABLE = parameter.ENERGY_CO2_ELECTRO_RENEWABLE
        self.ENERGY_CO2_DIESEl = parameter.ENERGY_CO2_DIESEL
        self.ENERGY_CO2_EFUEL = parameter.ENERGY_CO2_EFUEL
        self.ENERGY_CO2_H2 = parameter.ENERGY_CO2_H2

        self.ENERGY_POLLUTANTS_ELECTRO_CASUAL = parameter.ENERGY_POLLUTANTS_ELECTRO_CASUAL
        self.ENERGY_POLLUTANTS_ELECTRO_RENEWABLE = parameter.ENERGY_POLLUTANTS_ELECTRO_RENEWABLE
        self.ENERGY_POLLUTANTS_DIESEL = parameter.ENERGY_POLLUTANTS_DIESEL
        self.ENERGY_POLLUTANTS_EFUEL = parameter.ENERGY_POLLUTANTS_EFUEL
        self.ENERGY_POLLUTANTS_H2 = parameter.ENERGY_POLLUTANTS_H2

        self.ENERGY_PRIMARYENERGY_ELECTRO_CASUAL = parameter.ENERGY_PRIMARYENERGY_ELECTRO_CASUAL
        self.ENERGY_PRIMARYENERGY_ELECTRO_RENEWABLE = parameter.ENERGY_PRIMARYENERGY_ELECTRO_RENEWABLE
        self.ENERGY_PRIMARYENERGY_DIESEL = parameter.ENERGY_PRIMARYENERGY_DIESEL
        self.ENERGY_PRIMARYENERGY_EFUEL = parameter.ENERGY_PRIMARYENERGY_EFUEL
        self.ENERGY_PRIMARYENERGY_H2 = parameter.ENERGY_PRIMARYENERGY_H2

        self.CO2_COST = parameter.CO2_COST
        self.UTILITY_POINT_PRIMARY_ENERGY = parameter.UTILITY_POINT_PRIMARY_ENERGY
        self.UTILITY_TO_MONEY = parameter.UTILITY_TO_MONEY

    def debt_service(self, vehicle_pattern):
        debt_service = vehicle_pattern.debt_service * self.tg.running_time_year
        return debt_service

    def maintenance_cost(self, vehicle_pattern):
        maintenance_cost = vehicle_pattern.maintenance_cost_km * self.tg.running_km_year
        return maintenance_cost

    def energy_cost(self, vehicle_pattern):
        if vehicle_pattern.type_of_traction == "Elektro":
            energy = self.energy_electro(vehicle_pattern)
            energy_cost = self.ENERGY_COST_ELECTRO_RENEWABLE * energy
            co2_energy_cost = energy * self.ENERGY_CO2_ELECTRO_RENEWABLE * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_ELECTRO_RENEWABLE * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_ELECTRO_RENEWABLE * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        elif vehicle_pattern.type_of_traction == "Diesel":
            energy = self.energy_diesel(vehicle_pattern)
            energy_cost = self.ENERGY_COST_DIESEL * energy
            co2_energy_cost = energy * self.ENERGY_CO2_DIESEl * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_DIESEL * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_DIESEL * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        elif vehicle_pattern.type_of_traction == "eFuel":
            energy = self.energy_diesel(vehicle_pattern)
            energy_cost = self.ENERGY_COST_EFUEL * energy
            co2_energy_cost = energy * self.ENERGY_CO2_EFUEL * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_EFUEL * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_EFUEL * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        else:
            energy_cost = 0
            co2_energy_cost = 0
            pollutants_cost = 0
            primary_energy_cost = 0
            logging.error(f"No fitting traction found {vehicle_pattern.type_of_traction}")

        return energy_cost, co2_energy_cost, pollutants_cost, primary_energy_cost

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
        co2_energy_cost_sum = 0
        pollutants_cost_sum = 0
        primary_energy_cost_sum = 0

        for vehicle in vehicles_list:
            vehicle_pattern = self._vehicle_pattern_by_traction(vehicle)
            debt_service = self.debt_service(vehicle_pattern)
            maintenance_cost = self.maintenance_cost(vehicle_pattern)
            energy_cost, co2_energy_cost, pollutants_cost, primary_energy_cost = self.energy_cost(vehicle_pattern)

            debt_service_sum += debt_service
            maintenance_cost_sum += maintenance_cost
            energy_cost_sum += energy_cost
            co2_energy_cost_sum += co2_energy_cost
            pollutants_cost_sum += pollutants_cost
            primary_energy_cost_sum += primary_energy_cost

            use += debt_service + maintenance_cost + energy_cost + co2_energy_cost + pollutants_cost + primary_energy_cost

        return use, debt_service_sum, maintenance_cost_sum, energy_cost_sum, co2_energy_cost_sum, pollutants_cost_sum, primary_energy_cost_sum

    def calc_barwert(self, use, debt_service_sum, maintenance_cost_sum, energy_cost_sum, co2_energy_cost_sum,
                     pollutants_cost_sum, primary_energy_cost_sum, start_year, duration):
        """

        :param duration:
        :param start_year:
        :param use:
        :param debt_service_sum:
        :param maintenance_cost_sum:
        :param energy_cost_sum:
        :return:
        """
        use_base_year = super().cost_base_year(start_year=start_year, duration=duration, cost=use, cost_is_sum=False)
        debt_service_base_year = super().cost_base_year(start_year=start_year, duration=duration, cost=debt_service_sum,
                                                        cost_is_sum=False)
        maintenance_cost_base_year = super().cost_base_year(start_year=start_year, duration=duration,
                                                            cost=maintenance_cost_sum, cost_is_sum=False)
        energy_cost_base_year = super().cost_base_year(start_year=start_year, duration=duration, cost=energy_cost_sum)
        co2_energy_cost_base_year = super().cost_base_year(start_year=start_year, duration=duration,
                                                           cost=co2_energy_cost_sum)
        pollutants_cost_base_year = super().cost_base_year(start_year=start_year, duration=duration,
                                                           cost=pollutants_cost_sum)
        primary_energy_cost_base_year = super().cost_base_year(start_year=start_year, duration=duration,
                                                               cost=primary_energy_cost_sum)

        return use_base_year, debt_service_base_year, maintenance_cost_base_year, energy_cost_base_year, co2_energy_cost_base_year, pollutants_cost_base_year, primary_energy_cost_base_year

    def _vehicle_pattern_by_traction(self, vehicle):
        """

        :return:
        """
        vehicle_pattern_transportmode = self._vehicle_pattern_by_transport_mode(vehicle)
        if vehicle_pattern_transportmode is None:
            if hasattr(self, 'tg'):
                id = self.tg
            elif hasattr(self, 'trainline'):
                id = self.trainline
            raise NoVehiclePatternExistsError(
                message=f"No Vehicle pattern for {id.id} and traction {self.traction}")

        match self.traction:
            case "electrification":
                vehicle_pattern = vehicle_pattern_transportmode.vehicle_pattern_electrical
            case "h2":
                vehicle_pattern = vehicle_pattern_transportmode.vehicle_pattern_h2
            case "battery":
                vehicle_pattern = vehicle_pattern_transportmode.vehicle_pattern_battery
            case "efuel":
                vehicle_pattern = vehicle_pattern_transportmode.vehicle_pattern_efuel
            case "diesel":
                vehicle_pattern = vehicle_pattern_transportmode.vehicle_pattern_diesel
            case _:
                raise NoTractionFoundError(message=f"Traction {self.traction} is not a valid case")

        if vehicle_pattern is None:
            if hasattr(self, 'tg'):
                id = self.tg
            elif hasattr(self, 'trainline'):
                id = self.trainline
            raise NoVehiclePatternExistsError(
                message=f"No Vehicle pattern for {id} and traction {self.traction}")

        return vehicle_pattern

    def _vehicle_pattern_by_transport_mode(self, vehicle):
        """

        :param vehicle:
        :return:
        """
        # TODO: Change that so no querry is needed
        match self.transport_mode:
            case 'spfv':
                vehicle_pattern_transportmode = vehicle.vehicle_pattern_spfv
            case 'spnv':
                vehicle_pattern_transportmode = vehicle.vehicle_pattern_spnv
            case 'sgv':
                vehicle_pattern_transportmode = vehicle.vehicle_pattern_sgv
            case _:
                raise NoTransportmodeFoundError(message=f"There is no transportmode called {self.transport_mode}")

        # vehicle_pattern_transportmode = VehiclePattern.query.get(vehicle_pattern_id_transportmode)

        return vehicle_pattern_transportmode


class BvwpSgv(BvwpUse):
    def __init__(self, tg, traction, start_year_operation, duration_operation):
        self.transport_mode = 'sgv'
        formation = get_formation_calculation_bvwp(tg.trains[0].train_part.formation)
        super().__init__(model=tg, tg_or_tl='tg', formation=formation, traction=traction, transport_mode='sgv')
        if self.vehicles[0].engine is True:
            self.loko = self.vehicles[0]
            self.waggon = self.vehicles[1]
        elif self.vehicles[0].wagon is True:
            self.loko = self.vehicles[1]
            self.waggon = self.vehicles[0]

        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum, self.co2_energy_cost_sum, self.pollutants_cost_sum, self.primary_energy_cost_sum = super().calc_use(
            vehicles_list=[self.loko])

        self.use_base_year, self.debt_service_base_year, self.maintenance_cost_base_year, self.energy_cost_base_year, self.co2_energy_cost_base_year, self.pollutants_cost_base_year, self.primary_energy_cost_base_year = super().calc_barwert(
            start_year=start_year_operation,
            duration=duration_operation,
            use=self.use,
            debt_service_sum=self.debt_service_sum,
            maintenance_cost_sum=self.maintenance_cost_sum,
            energy_cost_sum=self.energy_cost_sum,
            co2_energy_cost_sum=self.co2_energy_cost_sum,
            pollutants_cost_sum=self.pollutants_cost_sum,
            primary_energy_cost_sum=self.primary_energy_cost_sum
        )

    def energy_electro(self, vehicle_pattern):
        # factor 1000 to get the value in [l]
        energy = 1.08 * (self.waggon.brutto_weight ** (-0.62)) * self.tg.running_km_year * 1000
        return energy

    def energy_diesel(self, vehicle_pattern):
        # factor 1000 to get the value in [l]
        energy = 0.277 * (self.waggon.brutto_weight ** (-0.62)) * self.tg.running_km_year * 1000
        return energy


class BvwpSpfv(BvwpUse):
    def __init__(self, tg, traction, start_year_operation, duration_operation):
        self.transport_mode = 'spfv'
        formation = get_formation_calculation_bvwp(tg.trains[0].train_part.formation)
        super().__init__(model=tg, tg_or_tl='tg', formation=formation, traction=traction, transport_mode='spfv')

        # TODO: Add co2_energy_cost, pollutants_cost, primary_energy_cost
        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum, self.co2_energy_cost_sum, self.pollutants_cost_sum, self.primary_energy_cost_sum = super().calc_use(
            vehicles_list=self.vehicles)
        self.use_base_year, self.debt_service_base_year, self.maintenance_cost_base_year, self.energy_cost_base_year, self.co2_energy_cost_base_year, self.pollutants_cost_base_year, self.primary_energy_cost_base_year = super().calc_barwert(
            start_year=start_year_operation,
            duration=duration_operation,
            use=self.use,
            debt_service_sum=self.debt_service_sum,
            maintenance_cost_sum=self.maintenance_cost_sum,
            energy_cost_sum=self.energy_cost_sum,
            co2_energy_cost_sum=self.co2_energy_cost_sum,
            pollutants_cost_sum=self.pollutants_cost_sum,
            primary_energy_cost_sum=self.primary_energy_cost_sum
        )

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
    def __init__(self, tg, traction, start_year_operation, duration_operation):
        self.transport_mode = 'spnv'
        formation = get_formation_calculation_bvwp(tg.trains[0].train_part.formation)
        super().__init__(model=tg, tg_or_tl='tg', formation=formation, traction=traction, transport_mode='spnv')

        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum, self.co2_energy_cost_sum, self.pollutants_cost_sum, self.primary_energy_cost_sum = super().calc_use(
            vehicles_list=self.vehicles)
        self.use_base_year, self.debt_service_base_year, self.maintenance_cost_base_year, self.energy_cost_base_year, self.co2_energy_cost_base_year, self.pollutants_cost_base_year, self.primary_energy_cost_base_year = super().calc_barwert(
            start_year=start_year_operation,
            duration=duration_operation,
            use=self.use,
            debt_service_sum=self.debt_service_sum,
            maintenance_cost_sum=self.maintenance_cost_sum,
            energy_cost_sum=self.energy_cost_sum,
            co2_energy_cost_sum=self.co2_energy_cost_sum,
            pollutants_cost_sum=self.pollutants_cost_sum,
            primary_energy_cost_sum=self.primary_energy_cost_sum
        )

    def energy_electro(self, vehicle_pattern):
        energy_km = self.tg.running_km_year * vehicle_pattern.energy_per_km
        energy_time = self.tg.running_time_year * vehicle_pattern.energy_consumption_hour
        energy = energy_km + energy_time
        return energy

    # TODO: Does energy_diesel also need update??


class StandiSpnv(BvwpUse):
    def __init__(self, trainline, traction, start_year_operation, duration_operation, recalculate_count_formations=False):
        formation = get_formation_calculation_standi(trainline.train_groups[0].trains[0].train_part.formation)
        super().__init__(model=trainline, tg_or_tl='tl', formation=formation, traction=traction, transport_mode='spnv')
        if recalculate_count_formations is True:
            self.train_cycles = len(self.trainline.get_train_cycle())
        else:
            self.train_cycles = self.trainline.count_formations

        self.use, self.debt_service_sum, self.maintenance_cost_sum, self.energy_cost_sum, self.co2_energy_cost_sum, self.pollutants_cost_sum, self.primary_energy_cost_sum = self.calc_use()
        self.use_base_year, self.debt_service_base_year, self.maintenance_cost_base_year, self.energy_cost_base_year, self.co2_energy_cost_base_year, self.pollutants_cost_base_year, self.primary_energy_cost_base_year = super().calc_barwert(
            start_year=start_year_operation,
            duration=duration_operation,
            use=self.use,
            debt_service_sum=self.debt_service_sum,
            maintenance_cost_sum=self.maintenance_cost_sum,
            energy_cost_sum=self.energy_cost_sum,
            co2_energy_cost_sum=self.co2_energy_cost_sum,
            pollutants_cost_sum=self.pollutants_cost_sum,
            primary_energy_cost_sum=self.primary_energy_cost_sum
        )

    def calc_use(self):
        use = 0

        debt_service = self.debt_service()
        maintenance_cost_time = self.maintenance_cost_time()

        energy_cost_sum = 0
        co2_energy_cost_sum = 0
        pollutants_cost_sum = 0
        primary_energy_cost_sum = 0
        maintenance_cost_running_sum = 0

        for tg in self.traingroups:
            formation = get_formation_calculation_standi(tg.trains[0].train_part.formation)
            vehicles = formation.vehicles_composition
            for vehicle in vehicles:
                vehicle_pattern = super()._vehicle_pattern_by_traction(vehicle=vehicle)
                energy_cost, co2_energy_cost, pollutants_cost, primary_energy_cost = self.energy_cost(vehicle_pattern=vehicle_pattern, traingroup=tg)
                maintenance_cost_running = self.maintenance_cost_running(vehicle_pattern=vehicle_pattern, traingroup=tg)

                energy_cost_sum += energy_cost
                maintenance_cost_running_sum += maintenance_cost_running
                co2_energy_cost_sum += co2_energy_cost
                pollutants_cost_sum += pollutants_cost
                primary_energy_cost_sum += primary_energy_cost

        maintenance_cost_sum = maintenance_cost_time + maintenance_cost_running_sum
        use += debt_service
        use += maintenance_cost_time
        use += energy_cost_sum
        use += maintenance_cost_running_sum
        use += co2_energy_cost_sum
        use += pollutants_cost_sum
        use += primary_energy_cost_sum

        return use, debt_service, maintenance_cost_sum, energy_cost_sum, co2_energy_cost_sum, pollutants_cost_sum, primary_energy_cost_sum

    def debt_service(self):
        debt_service_vehicles = 0
        for vehicle in self.vehicles:
            vehicle_pattern = super()._vehicle_pattern_by_traction(vehicle=vehicle)
            debt_service_vehicles += vehicle_pattern.debt_service

        count_formations = self.train_cycles

        debt_service = count_formations * debt_service_vehicles

        return debt_service

    def maintenance_cost_running(self, vehicle_pattern, traingroup):
        additional_maintenance_battery = vehicle_pattern.additional_maintenance_cost_withou_overhead * (traingroup.running_km_year_no_catenary/traingroup.running_km_year)
        maintenance_cost = (1 + additional_maintenance_battery) * vehicle_pattern.maintenance_cost_km * traingroup.running_km_year

        return maintenance_cost

    def maintenance_cost_time(self):
        maintenance_cost_time_vehicles = 0
        for vehicle in self.vehicles:
            vehicle_pattern = super()._vehicle_pattern_by_traction(vehicle=vehicle)
            maintenance_cost_time_vehicles += vehicle_pattern.maintenance_cost_duration_t * vehicle.vehicle_pattern.weight

        count_formations = self.train_cycles

        maintenance_cost_time = count_formations * maintenance_cost_time_vehicles / 1000

        return maintenance_cost_time

    def energy_cost(self, vehicle_pattern, traingroup):

        if vehicle_pattern.type_of_traction == "Elektro" or vehicle_pattern.type_of_traction == "Batterie":
            energy = self.energy(vehicle_pattern=vehicle_pattern, traingroup=traingroup)
            energy_cost = self.ENERGY_COST_ELECTRO_RENEWABLE * energy
            co2_energy_cost = energy * self.ENERGY_CO2_ELECTRO_RENEWABLE * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_ELECTRO_RENEWABLE * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_ELECTRO_RENEWABLE * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        elif vehicle_pattern.type_of_traction == "Diesel":
            energy = self.energy(vehicle_pattern=vehicle_pattern, traingroup=traingroup)
            energy_cost = self.ENERGY_COST_DIESEL * energy
            co2_energy_cost = energy * self.ENERGY_CO2_DIESEl * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_DIESEL * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_DIESEL * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        elif vehicle_pattern.type_of_traction == "eFuel":
            energy = self.energy(vehicle_pattern=vehicle_pattern, traingroup=traingroup)
            energy_cost = self.ENERGY_COST_EFUEL * energy
            co2_energy_cost = energy * self.ENERGY_CO2_EFUEL * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_EFUEL * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_EFUEL * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        elif vehicle_pattern.type_of_traction == "H2":
            energy = self.energy(vehicle_pattern=vehicle_pattern, traingroup=traingroup)
            energy_cost = self.ENERGY_COST_H2 * energy
            co2_energy_cost = energy * self.ENERGY_CO2_H2 * self.CO2_COST * 10 ** (-6)
            pollutants_cost = energy * self.ENERGY_POLLUTANTS_H2 * 10 ** (-2)
            primary_energy_cost = energy * self.ENERGY_PRIMARYENERGY_H2 * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_POINT_PRIMARY_ENERGY * self.UTILITY_TO_MONEY * 10 ** (
                -3)

        else:
            raise NoTractionFoundError(
            message=f"No Traction found for {self.trainline} and traction {self.traction}")

        return energy_cost, co2_energy_cost, pollutants_cost, primary_energy_cost

    def energy(self, vehicle_pattern, traingroup):
        additional_battery = vehicle_pattern.additional_energy_without_overhead * (traingroup.length_line_no_catenary/traingroup.length_line)
        energy_per_km = vehicle_pattern.energy_per_km

        energy_running = (1 + additional_battery) * energy_per_km * traingroup.running_km_year

        # calculate energy usage through stops
        intermediate_1 = 55.6 * (
                    traingroup.travel_time.total_seconds() / 60 - traingroup.stops_duration.total_seconds() / 60)
        segments = traingroup.stops_count - 1
        try:
            reference_speed = 3.6 / (vehicle_pattern.energy_stop_a * segments) * (intermediate_1 - math.sqrt(
                intermediate_1 ** 2 - 2 * vehicle_pattern.energy_stop_a * segments * (traingroup.length_line * 1000)))
        except ValueError:
            logging.info(
                f'Could not calculate reference speed for line {self.trainline}. More information on page 197 Verfahrensanleitung Standardisierte Bewertung')
            reference_speed = 160
        energy_per_stop = vehicle_pattern.energy_stop_b * (reference_speed ** 2) * vehicle_pattern.weight * (10 ** (-6))
        energy_stops = energy_per_stop * (traingroup.stops_count_year / 1000)
        energy = energy_running + energy_stops

        return energy


if __name__ == "__main__":
    # tg_id = "tg_100_x0020_G_x0020_2500_113810"
    # sgv = BvwpSgv(tg_id, start_year_operation=2030, duration_operation=30, traction='diesel')
    # print(f"diesel {sgv.use}")
    # sgv = BvwpSgv(tg_id, start_year_operation=2030, duration_operation=30, traction='electrification')
    # print(f"electrification {sgv.use}")
    # sgv = BvwpSgv(tg_id, start_year_operation=2030, duration_operation=30, traction='efuel')
    # print(f"efuel {sgv.use}")

    # tg_id = "tg_FV34.a_x0020_B_x0020_34001_128185"
    # spfv = BvwpSpfv(tg_id, traction='electrification', start_year_operation=2030, duration_operation=30)
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

    spnv = StandiSpnv(trainline_id, traction='electrification', start_year_operation=2030, duration_operation=30)
    print(spnv.use)
