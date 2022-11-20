"""automatic migration

Revision ID: b3ec2a349989
Revises: b9f6a5c2cf8b
Create Date: 2022-11-20 15:01:27.778039

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3ec2a349989'
down_revision = 'b9f6a5c2cf8b'
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
    op.drop_constraint('railway_tunnels_route_number_id_fkey', 'railway_tunnels', type_='foreignkey')
    op.create_foreign_key(None, 'railway_tunnels', 'railway_route', ['route_number_id'], ['number'])
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'railway_tunnels', type_='foreignkey')
    op.create_foreign_key('railway_tunnels_route_number_id_fkey', 'railway_tunnels', 'railway_route', ['route_number_id'], ['id'])
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
