from tests.base import BaseTestCase
from prosd import db
from prosd.manage_db.version import Version
from prosd.models import TimetableTrainGroup, RailwayLine, RouteTraingroup
from prosd.calculation_methods.cost import BvwpProjectBattery
from prosd.graph.railgraph import RailGraph

import pandas
import os


def calculate_battery(source, sink):
    rg = RailGraph()
    graph = rg.load_graph(rg.filepath_save_with_station_and_parallel_connections)
    path = rg.shortest_path_between_stations(graph=graph, station_from=source, station_to=sink)
    railway_lines_scope = path["edges"]
    train_groups = db.session.query(TimetableTrainGroup).join(RouteTraingroup).filter(RouteTraingroup.railway_line_id.in_(railway_lines_scope)).all()

    dirname = os.path.dirname(__file__)
    filepath_changes = os.path.join(dirname, '../../example_data/versions/version_test.csv')
    version_test = Version(filepath_changes=filepath_changes)
    version_test.load_changes()

    """code to test"""
    battery = BvwpProjectBattery(start_year_planning=2022, rl_id_scope = railway_lines_scope, infra_version=version_test, train_groups=train_groups)


class TestCostBattery(BaseTestCase):
    def test_cost_battery_testcase1(self):
        """
        Test the calculation cost of battery, testcase 1
        :return:
        """
        """preperation"""

        calculate_battery(source='TKT', sink='TOL')

    def test_cost_battery_testcase2(self):
        """
        Stolberg KST – Breinig KBRN
        :return:
        """
        calculate_battery(source='KBRN', sink='KST')

    def test_cost_battery_testcase3(self):
        """

        :return:
        """
        calculate_battery(source='AWE', sink='ADB')

