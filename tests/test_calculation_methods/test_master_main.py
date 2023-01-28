from tests.base import BaseTestCase

from prosd.manage_db.version import Version
from scripts.masterarbeit import master_main
from prosd.models import MasterScenario, MasterArea
from prosd import parameter

area_id = 73

def get_infra_version(scenario_id):
    scenario = MasterScenario.query.get(scenario_id)
    scenario_infra = Version(scenario=scenario)
    return scenario_infra


class TestMasterMain(BaseTestCase):



