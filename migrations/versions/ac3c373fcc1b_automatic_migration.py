"""automatic migration

Revision ID: ac3c373fcc1b
Revises: c9d22681817b
Create Date: 2022-10-01 20:38:36.169597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ac3c373fcc1b'
down_revision = 'c9d22681817b'
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
    op.add_column('projects_contents', sa.Column('new_station', sa.Boolean(), nullable=True))
    op.add_column('projects_contents', sa.Column('depot', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('projects_contents', 'depot')
    op.drop_column('projects_contents', 'new_station')
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

