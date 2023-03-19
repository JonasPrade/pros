from prosd import parameter


class BaseCalculation:
    # base methods for the use-cost-calculation of the calculation_methods
    def __init__(self):
        self.BASE_YEAR = parameter.BASE_YEAR
        self.p = parameter.RATE

    def cost_base_year(self, start_year, duration, cost, cost_is_sum=True):
        """

        :param start_year:
        :param duration:
        :param cost:
        :param cost_is_sum: the given cost is the summed up costs. if no, the costs are for one year
        :return:
        """
        if cost_is_sum:
            cost_year = cost / duration
        else:
            cost_year = cost

        cost_base_sum = 0

        for x in range(duration):
            n = start_year - self.BASE_YEAR + x
            cost_base = cost_year / ((1 + self.p) ** n)
            cost_base_sum += cost_base

        return cost_base_sum
