from tests.base import BaseTestCase
from prosd.manage_db.version import Version
from prosd.models import MasterScenario, RailwayLine

def get_infra_version():
    scenario_id = 1
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)

    return scenario_infra

class TestVersion(BaseTestCase):
    # def test_change_electrification(self):
    #     dirname = os.path.dirname(__file__)
    #     filepath_changes = os.path.join(dirname, '../../example_data/versions/version_test.csv')
    #     version_test = Version(filepath_changes=filepath_changes)
    #
    #     catenary_old = version_test.infra["railway_lines"][
    #         version_test.infra["railway_lines"].railway_line_id == 41088].railway_line_model.iloc[0].catenary
    #     version_test.load_changes()
    #     catenary = version_test.infra["railway_lines"][
    #         version_test.infra["railway_lines"].railway_line_id == 41088].railway_line_model.iloc[0].catenary
    #
    #     self.assertTrue(catenary_old is False and catenary is True)

    # def test_change_charging_station(self):
    #     dirname = os.path.dirname(__file__)
    #     filepath_changes = os.path.join(dirname, '../../example_data/versions/version_test.csv')
    #     version_test = Version(filepath_changes=filepath_changes)
    #
    #     charging_old = version_test.infra["railway_stations"][
    #         version_test.infra["railway_stations"].railway_station_id == 3738].railway_station_model.iloc[0].charging_station
    #     if charging_old is None:
    #         charging_old = False
    #     version_test.load_changes()
    #     charging = version_test.infra["railway_stations"][
    #         version_test.infra["railway_stations"].railway_station_id == 3738].railway_station_model.iloc[
    #         0].charging_station
    #     self.assertTrue(charging_old is False and charging is True)

    def test_add_and_delete_electrification(self):
        infra_version = get_infra_version()
        rw_line_id = 20832
        rw_line = RailwayLine.query.get(rw_line_id)
        catenary_before_adding = rw_line.catenary
        infra_version._add_electrification(rw_line)
        catenary_after_adding = rw_line.catenary
        infra_version._remove_electrification(rw_line)
        catenary_after_remove = rw_line.catenary
        self.assertTrue(
            catenary_before_adding is False and catenary_after_adding is True and catenary_after_remove is False
        )

    def test_add_and_delete_electrification_to_dataframe(self):
        infra_version = get_infra_version()
        rw_line_id = 20832
        rw_line = RailwayLine.query.get(rw_line_id)
        catenary_before_adding = infra_version.get_railwayline_model(rw_line_id).catenary
        infra_version.add_electrification_for_rw_lines([rw_line])
        catenary_after_adding = infra_version.get_railwayline_model(rw_line_id).catenary
        infra_version.remove_electrification_for_rw_lines([rw_line])
        catenary_after_remove = infra_version.get_railwayline_model(rw_line_id).catenary
        self.assertTrue(
            catenary_before_adding is False and catenary_after_adding is True and catenary_after_remove is False
        )