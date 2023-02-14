import json
from tests.base import BaseTestCase

project_id = 4
traingroup_id = "tg_BY15_X_x0020_15001_4393"
station_id = 2
railwaypoint_id = 45819
masterarea_id = 60
masterscenario_id = 1
#
# api_key_headers = Headers({
#             'x-api-key': 'TEST-API-KEY'
#         })
#         headers = kwargs.pop('headers', Headers())
#         headers.extend(api_key_headers)
#         kwargs['headers'] = headers


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
            self.assertTrue(len(data['projectgroups']) >0 )
            self.assertEqual(response.status_code, 200)

    def test_get_first_projectgroup(self):
        with self.client:
            api_string = f"/projectgroup/first"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['projectgroup']) >0 )
            self.assertEqual(response.status_code, 200)

    def test_get_traingroup(self):
        with self.client:
            api_string = f"/traingroup/{traingroup_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['traingroup']) >0)
            self.assertEqual(response.status_code, 200)

    def test_get_station(self):
        with self.client:
            api_string = f"/station/{station_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['station']) >0)
            self.assertEqual(response.status_code, 200)

    def test_get_railway_point(self):
        with self.client:
            api_string = f"/railwaypoint/{railwaypoint_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['point']) >0)
            self.assertEqual(response.status_code, 200)

    def test_get_masterarea(self):
        with self.client:
            api_string = f"/masterarea/{masterarea_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_area']) >0)
            self.assertEqual(response.status_code, 200)

    def test_get_masterscenario(self):
        with self.client:
            api_string = f"/masterscenario/{masterscenario_id}"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_scenario']) >0)
            self.assertEqual(response.status_code, 200)

    def test_get_all_masterscenarios(self):
        with self.client:
            api_string = f"/masterscenarios"
            response = get_api(self, api_string)
            data = json.loads(response.data.decode())
            self.assertTrue(len(data['master_scenario']) >0)
            self.assertEqual(response.status_code, 200)
