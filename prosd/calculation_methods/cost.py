import os
import pandas

from prosd.calculation_methods.base import BaseCalculation


class BvwpCost(BaseCalculation):
    def __init__(self, investment_cost, maintenance_cost, start_year_planning, abs_nbs="abs"):
        super().__init__()
        self.BASE_YEAR = 2015
        self.p = 0.017
        self.FACTOR_PLANNING = 0.18
        self.DURATION_PLANNING = 7
        self.DURATION_OPERATION = 20  # because this is only used for electrification
        self.ANUALITY_FACTOR = 0.0428
        # TODO: Check if electrification is really only lasting 20 years

        self.duration_build = self.duration_building(abs_nbs=abs_nbs)
        self.start_year_planning = start_year_planning
        self.start_year_building = self.start_year_planning + self.DURATION_PLANNING
        self.start_year_operation = self.start_year_building + self.duration_build
        self.end_year_operation = self.start_year_operation + self.DURATION_OPERATION

        self.investment_cost = investment_cost
        self.planning_cost = self.investment_cost * self.FACTOR_PLANNING
        self.maintenace_cost = maintenance_cost

        self.planning_cost_2015 = self.cost_base_year(start_year=start_year_planning, duration=self.DURATION_PLANNING, cost=self.planning_cost)
        self.investment_cost_2015 = self.cost_base_year(start_year=self.start_year_building, duration=self.duration_build, cost=self.investment_cost)
        self.maintenance_cost_2015 = self.cost_base_year(start_year=self.start_year_operation, duration=self.DURATION_OPERATION, cost=self.maintenace_cost, cost_is_sum=False)
        self.capital_service_cost_2015 = self.calc_capital_service_infrastructure(investment_cost_2015=self.investment_cost_2015)

        self.cost_2015 = self.planning_cost_2015 + self.investment_cost_2015 + self.maintenance_cost_2015

    def duration_building(self, abs_nbs):
        """
        calculates the duration of building, based on the calculations of the bvwp
        :param abs_nbs:
        :return:
        """
        dirname = os.path.dirname(__file__)
        self.FILEPATH_DURATION_BVWP = os.path.realpath(
            os.path.join(dirname, "settings/duration_build_rail_bvwp.csv"))
        table_duration = pandas.read_csv(self.FILEPATH_DURATION_BVWP, header=0, index_col=0)

        duration_building = self._duration_year(cost_list=table_duration[abs_nbs])

        return duration_building

    def calc_capital_service_infrastructure(self, investment_cost_2015):
        """

        :param investment_cost_2015:
        :return:
        """
        # TODO: Calculate capital service infrastructure
        capital_service_infrastructure = investment_cost_2015 * self.ANUALITY_FACTOR

        return capital_service_infrastructure

    def _duration_year(self, cost_list):
        for index, cost in cost_list.items():
            if self.investment_cost < cost:
                duration_year = index + 1
                break
        return duration_year


class BvwpCostElectrification(BvwpCost):
    # TODO: Think of cost of substation, maybe there is a more specific calculation possible
    def __init__(self, start_year_planning, railway_lines, abs_nbs='abs'):
        self.railway_lines = railway_lines
        self.MAINTENANCE_FACTOR = 0.014  # factor from standardisierte Bewertung Tabelle B-19
        self.COST_OVERHEAD = 588.271   # in thousand Euro

        self.length_no_catenary = self.calc_unelectrified_railway_lines()
        self.cost_overhead = self.length_no_catenary * self.COST_OVERHEAD
        self.cost_substation = 0

        self.investment_cost = self.cost_overhead + self.cost_substation
        self.maintenace_cost = self.investment_cost * self.MAINTENANCE_FACTOR
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost, start_year_planning=start_year_planning, abs_nbs=abs_nbs)

    def calc_unelectrified_railway_lines(self):
        """
        calculates the length of not electrified lines and returns them. if the line has two tracks, it will multiple the length
        :param railway_lines:
        :return:
        """
        length_no_catenary = 0
        for line in self.railway_lines:
            factor_length = 1
            if line.catenary == False:
                if line.number_tracks == 'zweigleisig':
                    factor_length = 2
                length_no_catenary += line.length * factor_length / 1000

        return length_no_catenary


class BvwpCostH2(BvwpCost):
    # TODO: Algorithm for caluclating cost of h2 infrastructure
    def __init__(self, start_year_planning, railway_lines, abs_nbs='abs'):
        self.MAINTENANCE_FACTOR_H2 = 0.03
        self.investment_cost = 1000000000  # TODO: find a algorithm to calculate necessary infrastructure
        # wasserstofftankstelle wohl 1.000.000 (1 Mio. €)
        self.maintenace_cost = self.investment_cost * self.MAINTENANCE_FACTOR_H2
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)


class BvwpProjectBattery(BvwpCost):
    # TODO: Algorithm for calculating cost of battery infrastructure
    def __init__(self, start_year_planning, railway_lines, abs_nbs='abs'):
        self.MAINTENANCE_FACTOR_POWER = 0.014
        self.investment_cost = 1000000000  # TODO: find an algorithm to calculate necessary infrastructure
        self.maintenace_cost = self.investment_cost * self.MAINTENANCE_FACTOR_POWER
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)


class BvwpProjectEFuel(BvwpCost):
    def __init__(self, start_year_planning, abs_nbs='abs'):
        self.investment_cost = 0
        self.maintenace_cost = 0
        super().__init__(investment_cost=self.investment_cost, maintenance_cost=self.maintenace_cost,
                         start_year_planning=start_year_planning, abs_nbs=abs_nbs)

