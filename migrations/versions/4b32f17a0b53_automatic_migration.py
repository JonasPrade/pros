"""automatic migration

Revision ID: 4b32f17a0b53
Revises: 3f6fd5bd281b
Create Date: 2022-11-23 20:46:44.453145

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4b32f17a0b53'
down_revision = '3f6fd5bd281b'
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
    op.add_column('route_traingroups', sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))
    op.alter_column('route_traingroups', 'traingroup_id',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    op.alter_column('route_traingroups', 'railway_line_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('route_traingroups', 'section',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_constraint('route_traingroups_traingroup_id_railway_line_id_key', 'route_traingroups', type_='unique')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('route_traingroups_traingroup_id_railway_line_id_key', 'route_traingroups', ['traingroup_id', 'railway_line_id'])
    op.alter_column('route_traingroups', 'section',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('route_traingroups', 'railway_line_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('route_traingroups', 'traingroup_id',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.drop_column('route_traingroups', 'id')
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

