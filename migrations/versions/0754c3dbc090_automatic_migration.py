"""automatic migration

Revision ID: 0754c3dbc090
Revises: 08bf96dd5ca7
Create Date: 2022-06-18 22:43:20.858325

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = '0754c3dbc090'
down_revision = '08bf96dd5ca7'
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
    op.add_column('railway_points', sa.Column('coordinates', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False))
    # op.create_index('idx_railway_points_coordinates', 'railway_points', ['coordinates'], unique=False, postgresql_using='gist', postgresql_ops={})
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_railway_points_coordinates', table_name='railway_points', postgresql_using='gist', postgresql_ops={})
    op.drop_column('railway_points', 'coordinates')
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

