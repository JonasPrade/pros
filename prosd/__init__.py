from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_cors import CORS

import os

app = Flask(__name__)

app_settings = os.getenv(
    'APP_SETTINGS',
    'prosd.conf.Config'
)
app.config.from_object(app_settings)
app.config['CORS-HEADERS'] = 'Content-Type'

CORS(app)
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
ma = Marshmallow(app)
migrate = Migrate(app, db)

from prosd import models
from prosd import manage_db
from prosd import views
from prosd import api

from prosd.auth.views import auth_blueprint

app.register_blueprint(auth_blueprint)
