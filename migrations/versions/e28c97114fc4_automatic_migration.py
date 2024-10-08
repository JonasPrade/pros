"""automatic migration

Revision ID: e28c97114fc4
Revises: a1fe4bbf734b
Create Date: 2022-11-20 15:26:57.134481

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e28c97114fc4'
down_revision = 'a1fe4bbf734b'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('railway_bridges',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('direction', sa.Integer(), nullable=True),
    sa.Column('von_km_i', sa.BigInteger(), nullable=True),
    sa.Column('bis_km_i', sa.BigInteger(), nullable=True),
    sa.Column('von_km_l', sa.String(length=100), nullable=True),
    sa.Column('bis_km_l', sa.String(length=100), nullable=True),
    sa.Column('length', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rwbridges_to_rwlines',
    sa.Column('rw_bridges_id', sa.Integer(), nullable=True),
    sa.Column('rw_lines.id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['rw_bridges_id'], ['railway_bridges.id'], ),
    sa.ForeignKeyConstraint(['rw_lines.id'], ['railway_lines.id'], )
    )
    # op.drop_table('spatial_ref_sys')
    # op.drop_index('budgets_year_and_finve_uindex', table_name='budgets')
    # op.alter_column('railway_lines', 'voltage',
    #            existing_type=postgresql.DOUBLE_PRECISION(precision=53),
    #            comment=None,
    #            existing_comment='[kV]',
    #            existing_nullable=True)
    op.drop_constraint('railway_lines_tunnel_id_fkey', 'railway_lines', type_='foreignkey')
    op.drop_column('railway_lines', 'tunnel_id')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('railway_lines', sa.Column('tunnel_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('railway_lines_tunnel_id_fkey', 'railway_lines', 'railway_tunnels', ['tunnel_id'], ['id'], ondelete='SET NULL')
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
    op.drop_table('rwbridges_to_rwlines')
    op.drop_table('railway_bridges')
    # ### end Alembic commands ###

