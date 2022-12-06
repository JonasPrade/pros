"""empty message

Revision ID: 15085e1040f3
Revises: d78f3a733336
Create Date: 2022-12-03 12:01:43.844162

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15085e1040f3'
down_revision = 'd78f3a733336'
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

