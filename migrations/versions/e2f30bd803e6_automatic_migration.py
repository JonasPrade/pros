"""automatic migration

Revision ID: e2f30bd803e6
Revises: 03d19a1990dc
Create Date: 2022-10-08 14:21:18.103453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f30bd803e6'
down_revision = '03d19a1990dc'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('spatial_ref_sys')
    # op.drop_index('budgets_year_and_finve_uindex', table_name='budgets')
    op.add_column('timetable_categories', sa.Column('transport_mode', sa.String(length=5), nullable=True))
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('timetable_categories', 'transport_mode')
    op.create_index('budgets_year_and_finve_uindex', 'budgets', ['budget_year', 'fin_ve'], unique=False)
    op.create_table('spatial_ref_sys',
    sa.Column('srid', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('auth_name', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
    sa.Column('auth_srid', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('srtext', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.Column('proj4text', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.CheckConstraint('(srid > 0) AND (srid <= 998999)', name='spatial_ref_sys_srid_check'),
    sa.PrimaryKeyConstraint('srid', name='spatial_ref_sys_pkey')
    )
    # ### end Alembic commands ###

