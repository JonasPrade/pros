import time
import logging


from tests.base import BaseTestCase

from prosd.models import MasterArea, MasterScenario, TimetableTrainGroup
from prosd.manage_db.version import Version

tg_id = 'tg_300_x0020_G_x0020_1027_126692'
scenario_id = 1
logging.basicConfig(encoding='utf-8', level=logging.INFO)

class TestTimetableTrainGroup(BaseTestCase):

    def test_calc_cost_road_transport(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        cost_road_transport = tg.calc_cost_road_transport()
        self.assertTrue(cost_road_transport > 0)

    def test_get_wagon_sgv(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        vehicle = tg.get_wagon_sgv
        self.assertTrue(vehicle.brutto_weight > 0)

    def test_count_wagons(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        count_wagons = tg.count_wagons
        self.assertTrue(count_wagons > 0)

    def test_payload_train(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        payload_train = tg.payload_train
        self.assertTrue(payload_train > 0)

    def test_calc_wagon_cost_per_day(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        cost_wagons = tg.wagon_cost_per_day(scenario_id=scenario_id)
        self.assertTrue(cost_wagons > 0)

    def test_personnel_cost(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        personnel_cost = tg.personnel_cost_per_day(scenario_id=scenario_id)
        self.assertTrue(personnel_cost > 0)

    def test_train_provision_cost(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        provision_cost = tg.train_provision_cost_day
        self.assertTrue(provision_cost > 0)

    def test_running_km_day(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        start_time = time.time()

        running_km_day = tg.running_km_day(scenario_id)
        time_needed = time.time() - start_time
        logging.info(f'TimetableTrainGroup.running_km_day runs in {time_needed}')
        self.assertTrue(running_km_day > 0)

    def test_length_line(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        start_time = time.time()
        running_km_day = tg.length_line(scenario_id)
        time_needed = time.time() - start_time
        logging.info(f'TimetableTrainGroup.length_line runs in {time_needed}')
        self.assertTrue(running_km_day > 0)

    def test_rw_lines_for_scenario(self):
        tg = TimetableTrainGroup.query.get(tg_id)
        start_time = time.time()
        running_km_day = tg.railway_lines_scenario(scenario_id)
        time_needed = time.time() - start_time
        logging.info(f'TimetableTrainGroup.railway_lines_scenario runs in {time_needed}')
        self.assertTrue(len(running_km_day) > 0)


