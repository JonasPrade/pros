"""automatic migration

Revision ID: 071478e2151b
Revises: 916cd9e485f6
Create Date: 2022-11-01 17:23:45.205249

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '071478e2151b'
down_revision = '916cd9e485f6'
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
    # op.alter_column('railway_lines', 'voltage',
    #            existing_type=postgresql.DOUBLE_PRECISION(precision=53),
    #            comment=None,
    #            existing_comment='[kV]',
    #            existing_nullable=True)
    op.add_column('vehicles_pattern', sa.Column('vehicle_pattern_id_electrical', sa.Integer(), nullable=True))
    op.add_column('vehicles_pattern', sa.Column('vehicle_pattern_id_h2', sa.Integer(), nullable=True))
    op.add_column('vehicles_pattern', sa.Column('vehicle_pattern_id_battery', sa.Integer(), nullable=True))
    op.add_column('vehicles_pattern', sa.Column('vehicle_pattern_id_efuel', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'vehicles_pattern', 'vehicles_pattern', ['vehicle_pattern_id_efuel'], ['id'])
    op.create_foreign_key(None, 'vehicles_pattern', 'vehicles_pattern', ['vehicle_pattern_id_h2'], ['id'])
    op.create_foreign_key(None, 'vehicles_pattern', 'vehicles_pattern', ['vehicle_pattern_id_electrical'], ['id'])
    op.create_foreign_key(None, 'vehicles_pattern', 'vehicles_pattern', ['vehicle_pattern_id_battery'], ['id'])
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'vehicles_pattern', type_='foreignkey')
    op.drop_constraint(None, 'vehicles_pattern', type_='foreignkey')
    op.drop_constraint(None, 'vehicles_pattern', type_='foreignkey')
    op.drop_constraint(None, 'vehicles_pattern', type_='foreignkey')
    op.drop_column('vehicles_pattern', 'vehicle_pattern_id_efuel')
    op.drop_column('vehicles_pattern', 'vehicle_pattern_id_battery')
    op.drop_column('vehicles_pattern', 'vehicle_pattern_id_h2')
    op.drop_column('vehicles_pattern', 'vehicle_pattern_id_electrical')
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
    # ### end Alembic commands ###

