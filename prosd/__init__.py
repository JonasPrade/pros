from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from prosd.conf import sql_conf
# TODO: Change conf.py to real conf setup

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = sql_conf
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from prosd import models
from prosd import manage_db
