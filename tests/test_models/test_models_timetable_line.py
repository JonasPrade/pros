from tests.base import BaseTestCase
from prosd.models import TimetableLine

tt_id = 1720


class TestTimetableLine(BaseTestCase):
    def test_timetableline_all_trains(self):
        tt = TimetableLine.query.get(tt_id)
        df_all_trains = tt.all_trains
        self.assertTrue(df_all_trains.size == 36)

    def test_start_ocps(self):
        tt = TimetableLine.query.get(tt_id)
        ocps = tt.start_ocps
        self.assertTrue(ocps)

    def test_get_train_cycles_each_starting_ocp(self):
        tt = TimetableLine.query.get(tt_id)
        cycles = tt.get_train_cycles_each_starting_ocp()
        self.assertTrue(cycles)

