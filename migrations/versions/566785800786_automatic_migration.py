"""automatic migration

Revision ID: 566785800786
Revises: cf8ed14a3ea6
Create Date: 2022-11-05 23:39:49.081151

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '566785800786'
down_revision = 'cf8ed14a3ea6'
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
    op.add_column('railway_electricity_stations', sa.Column('electricity_station_type_id', sa.Integer(), nullable=True))
    op.drop_constraint('railway_electricity_stations_switching_station_id_fkey', 'railway_electricity_stations', type_='foreignkey')
    op.create_foreign_key(None, 'railway_electricity_stations', 'railway_electricity_station_types', ['electricity_station_type_id'], ['id'])
    op.create_foreign_key(None, 'railway_electricity_stations', 'railway_electricity_switching_stations', ['switching_station_id'], ['id'])
    # op.alter_column('railway_lines', 'voltage',
    #            existing_type=postgresql.DOUBLE_PRECISION(precision=53),
    #            comment=None,
    #            existing_comment='[kV]',
    #            existing_nullable=True)
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('railway_lines', 'voltage',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               comment='[kV]',
               existing_nullable=True)
    op.drop_constraint(None, 'railway_electricity_stations', type_='foreignkey')
    op.drop_constraint(None, 'railway_electricity_stations', type_='foreignkey')
    op.create_foreign_key('railway_electricity_stations_switching_station_id_fkey', 'railway_electricity_stations', 'railway_electricity_station_types', ['switching_station_id'], ['id'])
    op.drop_column('railway_electricity_stations', 'electricity_station_type_id')
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

