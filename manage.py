from flask.cli import FlaskGroup
from prosd import app, db

cli = FlaskGroup(app)

# TODO: Add cli command for creating an user


"""
@cli.command("create_db")
def create_db():
    db.drop_all()
    db.create_all()
    db.session.commmit()
"""

if __name__ == '__main__':
    cli()
