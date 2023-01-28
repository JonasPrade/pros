from flask_testing import TestCase
import subprocess
from datetime import datetime
import gzip

import prosd.conf
from prosd import app, db


def create_backup_from_prod():
    """
    creates a backup from the production environment
    :return:
    """
    config = prosd.conf.ProductionConfig
    now = datetime.now()
    TIMESTAMP = now.strftime('%Y-%m-%d-%H-%M-%S')
    FILE = f'/Users/jonas/PycharmProjects/pros/example_data/backup_test/{config.DATABASE_NAME}-{config.DATABASE_MODE}-{TIMESTAMP}.sql'
    database_complete_name = config.DATABASE_NAME+'-'+config.DATABASE_MODE
    pg_dump_command = '/Applications/Postgres.app/Contents/Versions/14/bin/pg_dump'

    # command = f'pg_dump -h {config.HOST} -d {database_complete_name} -U {config.USER} -w {config.PASSWORD} -p {config.PORT} -file {FILE}'
    command = [pg_dump_command,
               f'--dbname={config.SQLALCHEMY_DATABASE_URI}',
               '-Fc',
               '-f', FILE,
               '-v']

    with open(FILE, 'wb') as f:
        popen = subprocess.Popen(
            command,
            stdout=f
        )
        popen.communicate()
        # TODO: Load that in a .gz file for more compact backup

    return FILE


def restore_to_test(file):
    """
    Restores a backup file to the test db
    :param file:
    :return:
    """
    config = prosd.conf.TestingConfig

    psql_command = '/Applications/Postgres.app/Contents/Versions/14/bin/psql'

    command = [psql_command,
                   f'--dbname={config.SQLALCHEMY_DATABASE_URI}',
                   '-v',
                   file]
    popen = subprocess.Popen(
        command,
        stdout=subprocess.PIPE
    )
    popen.communicate()


class BaseTestCase(TestCase):
    """ Base Tests """
    # TODO: Write function that loads a test db

    def create_app(self):
        app.config.from_object('prosd.conf.TestingConfig')
        return app

    # def setUp(self):
    #     db.create_all()
    #     db.session.commit()
    #     file = create_backup_from_prod()
    #     restore_to_test(file)
    #     # TODO: Load data from prosd-prod

    # def tearDown(self):
    #     db.session.remove()
    #     db.drop_all()


