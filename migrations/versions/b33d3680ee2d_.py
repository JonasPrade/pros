"""empty message

Revision ID: b33d3680ee2d
Revises: 4ec67bbe5d13
Create Date: 2023-01-14 13:36:08.949098

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b33d3680ee2d'
down_revision = '4ec67bbe5d13'
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
    op.add_column('projects_contents', sa.Column('maintenance_cost', sa.Float(), nullable=True))
    op.add_column('projects_contents', sa.Column('planning_cost', sa.Float(), nullable=True))
    op.add_column('projects_contents', sa.Column('capital_service_cost', sa.Float(), nullable=True))
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
    op.drop_column('projects_contents', 'capital_service_cost')
    op.drop_column('projects_contents', 'planning_cost')
    op.drop_column('projects_contents', 'maintenance_cost')
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

