from prosd import app
from flask_sqlalchemy import get_debug_queries


if __name__ == '__main__':
    app.config['SQLALCHEMY_ECHO'] = True
    app.run(debug=True)
