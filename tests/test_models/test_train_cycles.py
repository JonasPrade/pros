from tests.base import BaseTestCase

from prosd.models import TrainCycle, TrainCycleElement, TimetableLine

trainline_id = 2148


class TestTrainCycle(BaseTestCase):
    def test_create_all_train_cycles(self):
        train_cycles = TrainCycle.calculate_train_cycles(
            timetableline_id=trainline_id
        )
        self.assertTrue(len(train_cycles)>0)

    def test_get_train_cycles(self):
        train_cycles = TrainCycle.get_train_cycles(
            timetableline_id=trainline_id
        )

        self.assertTrue(len(train_cycles)>0)

    def test_one_train_cycle(self):
        trainline = TimetableLine.query.get(trainline_id)
        trains = trainline.get_one_train_cycle()
        self.assertTrue(len(trains) == 2)
