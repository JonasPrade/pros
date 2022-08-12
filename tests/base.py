from flask_testing import TestCase

import gzip
import sh
from prosd import app, db


class BaseTestCase(TestCase):
    """ Base Tests """
    # TODO: Write function that loads a test db

    def create_app(self):
        app.config.from_object('prosd.conf.TestingConfig')
        return app

    # def setUp(self):
    #     db.create_all()
    #     db.session.commit()

    # def tearDown(self):
    #     db.session.remove()
    #     db.drop_all()