"""automatic migration

Revision ID: 8b3546a30099
Revises: a38c7a03a47b
Create Date: 2022-08-14 19:18:10.300576

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8b3546a30099'
down_revision = 'a38c7a03a47b'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('spatial_ref_sys')
    # op.add_column('projects_contents', sa.Column('bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cost', sa.Float(), nullable=True))
    # op.drop_column('projects_contents', 'bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos')
    op.add_column('railway_stations', sa.Column('type', sa.String(length=10), nullable=True))
    op.drop_index('railway_stations_db_kuerzel_uindex', table_name='railway_stations')
    op.create_unique_constraint(None, 'railway_stations', ['db_kuerzel'])
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'railway_stations', type_='unique')
    op.create_index('railway_stations_db_kuerzel_uindex', 'railway_stations', ['db_kuerzel'], unique=False)
    op.drop_column('railway_stations', 'type')
    op.add_column('projects_contents', sa.Column('bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('projects_contents', 'bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cost')
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

