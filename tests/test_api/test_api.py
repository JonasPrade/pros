import json
from tests.base import BaseTestCase

project_id = 4
traingroup_id = "tg_ST20.a_X_x0020_20102_4148"
station_id = 7
railwaypoint_id = 45819
masterarea_id = 2382
masterscenario_id = 1
trainpart_id = 'tp_BY15_X_x0020_15001_4395'
projectgroup_id = 7
projectcontent_id = 95453
texttype_id = 1
bskaction_id = 156


def get_api(self, api_string):
    user = login_user(
        self=self,
        username='Benutzer1',
        password='test1234'
    )
    auth_token = user.json['auth_token']
    answ = self.client.get(
        api_string,
        headers={
            "Authorization": f"Bearer {auth_token}"
        },
        content_type='application/json'
    )
    return answ


def login_user(self, username, password):
    return self.client.post(
        '/auth/login',
        data=json.dumps(dict(
            username=username,
            password=password
        )),
        content_type='application/json',
    )


class TestApi(BaseTestCase):
    def test_get_project(self):
        with self.client:
            api_string = f"project/{project_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(data['status'] == 'success')
            self.assertEqual(response.status_code, 200)

    def test_get_all_projectgroup(self):
        with self.client:
            api_string = f"projectgroups"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['projectgroups']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_first_projectgroup(self):
        with self.client:
            api_string = f"/projectgroup/first"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['projectgroup']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_traingroup(self):
        with self.client:
            api_string = f"/traingroup/{traingroup_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['traingroup']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_trainpart(self):
        with self.client:
            api_string = f"/trainpart/{trainpart_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['trainpart']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_station(self):
        with self.client:
            api_string = f"/station/{station_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['station']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_railway_point(self):
        with self.client:
            api_string = f"/railwaypoint/{railwaypoint_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['point']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_masterarea(self):
        with self.client:
            api_string = f"/masterarea/{masterarea_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_area']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_masterscenario(self):
        with self.client:
            api_string = f"/masterscenario/{masterscenario_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_scenario']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_all_masterscenarios(self):
        with self.client:
            api_string = f"/masterscenarios"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_scenario']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_main_masterareas_for_scenario(self):
        with self.client:
            api_string = f"/main_masterareas_for_scenario/{masterscenario_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_areas']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_traction_for_optimised_electrification(self):
        with self.client:
            api_string = f"/masterarea_optimised_traingroups/{masterarea_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['tractions']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_running_km_for_master_scenario(self):
        with self.client:
            api_string = f"/traingroups-scenario/{masterscenario_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_scenario']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_cost_traingroup_scenario(self):
        with self.client:
            api_string = f"/traingroupcostscenario/{masterscenario_id}/{traingroup_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['train_cost']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_projectcontentsbygroup(self):
        with self.client:
            api_string = f"/projectcontentsbygroup/{projectgroup_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['pcs']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_projectcontentshortbyid(self):
        with self.client:
            api_string = f"/projectcontentshort/{projectcontent_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['pc']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_get_projectcontent(self):
        with self.client:
            api_string = f"/projectcontent/{projectcontent_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['pc']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_textbypcandtexttype(self):
        with self.client:
            api_string = f"/textbypcandtexttype/{projectcontent_id}/{texttype_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['texts']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_projectgroupsbyid(self):
        with self.client:
            api_string = f"/projectgroupsbyid?id={projectgroup_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['projectgroups']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_progress_subprojects(self):
        with self.client:
            api_string = f"/subprojects-progress/{projectcontent_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['progress']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_bkshandlungsfeld_all(self):
        with self.client:
            api_string = f"/bkshandlungsfeld-all"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['bkshandlungsfeld']) > 0)
            self.assertEqual(response.status_code, 200)

    def test_bksaction(self):
        with self.client:
            api_string= f"/bksaction/{bskaction_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['action']) > 0)
            self.assertEqual(response.status_code, 200)


