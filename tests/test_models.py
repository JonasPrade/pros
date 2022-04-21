import json
import unittest

from prosd import db
from prosd.models import User, Project
from tests.base import BaseTestCase


def register_user(self, email, password):
    return self.client.post(
        '/auth/register',
        data=json.dumps(dict(
            email=email,
            password=password
        )),
        content_type='application/json',
    )

def login_user(self, email, password):
    return self.client.post(
        '/auth/login',
        data=json.dumps(dict(
            email=email,
            password=password
        )),
        content_type='application/json',
    )

class TestUserModel(BaseTestCase):

    def test_encode_auth_token(self):
        user = User(
            email='test@test.com',
            password='test'
        )
        db.session.add(user)
        db.session.commit()
        auth_token = user.encode_auth_token(user.id)
        self.assertTrue(isinstance(auth_token, str))

    def test_decode_auth_token(self):
        user = User(
            email='test@test.com',
            password='test'
        )
        db.session.add(user)
        db.session.commit()
        auth_token = user.encode_auth_token(user.id)
        self.assertTrue(isinstance(auth_token, str))

        self.assertTrue(User.decode_auth_token(
            auth_token.decode("utf-8") ) == 1)


class TestProjectModel(BaseTestCase):
    def test_create_project(self):
        # create a simple project
        project = Project('Testprojekt', description='Testbeschreibung')
        db.session.add(project)
        db.session.commit()
        self.assertTrue(project.id == 1)

    def test_get_project(self):
        """ Test for getting a project """
        with self.client:
            response = register_user(self, 'joe@gmail.com', '123456')
            data = json.loads(response.data.decode())
            self.assertTrue(data['status'] == 'success')
            self.assertTrue(data['message'] == 'Successfully registered.')
            self.assertTrue(data['auth_token'])
            self.assertTrue(response.content_type == 'application/json')
            self.assertEqual(response.status_code, 201)
            # user login
            response = login_user(self, 'joe@gmail.com', '123456')
            data = json.loads(response.data.decode())
            self.assertTrue(data['status'] == 'success')
            self.assertTrue(data['message'] == 'Successfully logged in.')
            self.assertTrue(data['auth_token'])
            self.assertTrue(response.content_type == 'application/json')
            self.assertEqual(response.status_code, 200)

            # create a simple project
            project = Project('Testprojekt', description='Testbeschreibung')
            db.session.add(project)
            db.session.commit()
            self.assertTrue(project.id == 1)

            # get data for that project
            project_response = self.client.get(
                '/project/1',
                headers=dict(
                    Authorization='Bearer ' + json.loads(
                        response.data.decode()
                    )['auth_token']
                )
            )
            project_response = json.loads(project_response.data)
            project_data_input = {'project': {'description': 'Testbeschreibung', 'id': 1, 'name': 'Testprojekt', 'project_contents': [], 'project_groups': [], 'project_railway_lines': [], 'superior_project': None, 'superior_project_id': None}}
            self.assertTrue(project_response == project_data_input)

    def test_get_project_without_header(self):
        # create a simple project
        project = Project('Testprojekt', description='Testbeschreibung')
        db.session.add(project)
        db.session.commit()
        self.assertTrue(project.id == 1)

        # get data for that project
        project_response = self.client.get(
            '/project/1'
        )
        project_response = json.loads(project_response.data)
        self.assertTrue(project_response['status'] == 'fail')
        self.assertTrue(project_response['message'] == 'Provide a valid auth token.')


    def test_get_project_with_wrong_header(self):
        # create a simple project
        project = Project('Testprojekt', description='Testbeschreibung')
        db.session.add(project)
        db.session.commit()
        self.assertTrue(project.id == 1)

        # get data for that project
        project_response = self.client.get(
            '/project/1',
            headers=dict(
                Authorization='Bearer ' + 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2NTA1NzAyMTEsImlhdCI6MTY1MDU3MDIwNiwic3ViIjoxfQ.j_2fkraqPvH_7Z7hScuUtJx_PncWuGs_9n4'
            )
        )
        project_response = json.loads(project_response.data)
        self.assertTrue(project_response['status'] == 'fail')
        self.assertTrue(project_response['message'] == 'Invalid token. Please log in again.')


def test_get_project_without_existing_project(self):
        pass




if __name__ == '__main__':
    unittest.main()