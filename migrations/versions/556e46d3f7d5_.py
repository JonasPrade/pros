"""empty message

Revision ID: 556e46d3f7d5
Revises: a5ca04c5f474
Create Date: 2023-01-06 13:57:12.607226

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '556e46d3f7d5'
down_revision = 'a5ca04c5f474'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('timetable_train_cost',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('traingroup_id', sa.String(length=255), nullable=True),
    sa.Column('calculation_method', sa.String(length=10), nullable=True),
    sa.Column('master_scenario_id', sa.Integer(), nullable=True),
    sa.Column('traction', sa.String(length=255), nullable=True),
    sa.Column('cost', sa.Integer(), nullable=True, comment='sum of cost in T EUR per year'),
    sa.Column('debt_service', sa.Integer(), nullable=True),
    sa.Column('maintenance_cost', sa.Integer(), nullable=True),
    sa.Column('energy_cost', sa.Integer(), nullable=True),
    sa.Column('co2_cost', sa.Integer(), nullable=True),
    sa.Column('pollutants_cost', sa.Integer(), nullable=True),
    sa.Column('primary_energy_cost', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['master_scenario_id'], ['master_scenarios.id'], ),
    sa.ForeignKeyConstraint(['traingroup_id'], ['timetable_train_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # op.drop_table('spatial_ref_sys')
    # op.drop_index('budgets_year_and_finve_uindex', table_name='budgets')
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
    op.drop_table('timetable_train_cost')
    # ### end Alembic commands ###
