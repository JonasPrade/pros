import json
import unittest
import geoalchemy2
import sqlalchemy
import shapely

from prosd import db
from prosd.models import User, Project, RailwayNodes, RailwayLine, RailwayPoint
from tests.base import BaseTestCase

# TODO: Add username for all user Tests

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
            auth_token.decode("utf-8")) == 1)


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
            project_data_input = {
                'project': {'description': 'Testbeschreibung', 'id': 1, 'name': 'Testprojekt', 'project_contents': [],
                            'project_groups': [], 'project_railway_lines': [], 'superior_project': None,
                            'superior_project_id': None}}
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


class TestRailwayLine(BaseTestCase):
    def test_create_railline_from_old(self):
        line_old = RailwayLine.query.get(16)
        coordinates = line_old.coordinates
        railline_new = RailwayLine.create_railline_from_old(line_old, coordinates)
        self.assertIsInstance(railline_new, RailwayLine)

    def test_split_railwayline(self):
        old_line_id = 39601
        blade_point = RailwayPoint.query.get(50658).coordinates
        newline_1, newline_2 = RailwayLine.split_railwayline(old_line_id=old_line_id, blade_point=blade_point)

        with self.subTest():
            self.assertIsInstance(newline_1, RailwayLine)
        with self.subTest():
            self.assertIsInstance(newline_2, RailwayLine)

    def test_get_line_that_intersects_point(self):
        coordinate = RailwayNodes.query.get(240838).coordinate
        from_line = RailwayLine.query.get(39516)
        line = RailwayLine.get_line_that_intersects_point_excluding_line(coordinate, from_line)
        self.assertIsInstance(line, RailwayLine)

    def test_get_other_node_of_line(self):
        line = RailwayLine.query.get(16)
        node1 = line.start_node
        node2_id = RailwayLine.get_other_node_of_line(line, node1)
        self.assertIsInstance(node2_id, RailwayNodes)

    def test_get_next_point_of_line(self):
        line = RailwayLine.query.get(16)
        point = db.session.execute(sqlalchemy.select(geoalchemy2.func.ST_StartPoint(line.coordinates))).one()[0]
        next_point = RailwayLine.get_next_point_of_line(line, point)

    def test_get_angle_two_lines(self):
        line1 = RailwayLine.query.get(40147)
        line2 = RailwayLine.query.get(19046)
        node = RailwayNodes.query.get(332046)

        angle_check = RailwayLine.get_angle_two_lines(line1=line1, line2=line2, node=node)
        self.assertFalse(angle_check)

class TestRailwayNode(BaseTestCase):
    def test_add_node_no_existing(self):
        coordinate = shapely.geometry.Point(0,0)
        node = RailwayNodes.add_node_if_not_exists(coordinate)
        self.assertIsInstance(node, RailwayNodes)

if __name__ == '__main__':
    unittest.main()
