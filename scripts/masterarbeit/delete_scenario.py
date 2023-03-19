from prosd.models import MasterScenario
from prosd import db

scenario_id = 42

scenario = MasterScenario.query.get(scenario_id)
db.session.delete(scenario)
db.session.commit()


