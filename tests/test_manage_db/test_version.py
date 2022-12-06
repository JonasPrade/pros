import os
import unittest

from tests.base import BaseTestCase
from prosd.manage_db.version import Version


class TestVersion(BaseTestCase):
    def test_change_electrification(self):
        dirname = os.path.dirname(__file__)
        filepath_changes = os.path.join(dirname, '../../example_data/versions/version_test.csv')
        version_test = Version(filepath_changes=filepath_changes)

        catenary_old = version_test.infra["railway_lines"][
            version_test.infra["railway_lines"].railway_line_id == 41088].railway_line_model.iloc[0].catenary
        version_test.load_changes()
        catenary = version_test.infra["railway_lines"][
            version_test.infra["railway_lines"].railway_line_id == 41088].railway_line_model.iloc[0].catenary

        self.assertTrue(catenary_old is False and catenary is True)

    def test_change_charging_station(self):
        dirname = os.path.dirname(__file__)
        filepath_changes = os.path.join(dirname, '../../example_data/versions/version_test.csv')
        version_test = Version(filepath_changes=filepath_changes)

        charging_old = version_test.infra["railway_stations"][
            version_test.infra["railway_stations"].railway_station_id == 3738].railway_station_model.iloc[0].charging_station
        if charging_old is None:
            charging_old = False
        version_test.load_changes()
        charging = version_test.infra["railway_stations"][
            version_test.infra["railway_stations"].railway_station_id == 3738].railway_station_model.iloc[
            0].charging_station
        self.assertTrue(charging_old is False and charging is True)


