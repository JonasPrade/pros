# prosd
Projektinformationssystem Schiene Deutschland

## Setup
* add a conf.py to the folder prosd
  *  there define following attributes:
```
class Config(object):
    USER = 
    PASSWORD = 
    DB_TYPE = 'postgresql'
    HOST = 
    PORT = '5432'
    POSTGRES_BASE = 
    POSTGRES_URL = 
    DATABASE_NAME = 
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", POSTGRES_URL + DATABASE_NAME)
    SQLALCHEMY_TRACK_MODIFICATIONS = 
    SECRET_KEY = 
    BCRYPT_LOG_ROUNDS = 
    DEBUG = False
    API_KEY_OPENROUTESERVICE = 
```
+ Setup a Postgresql DB with Postgis add-on
+ the required python libraries are in the requirements.txt