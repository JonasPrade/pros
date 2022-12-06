"""empty message

Revision ID: d78f3a733336
Revises: a5a0ffafef03
Create Date: 2022-12-03 11:59:42.901221

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd78f3a733336'
down_revision = 'a5a0ffafef03'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    pass


def downgrade_():
    pass

