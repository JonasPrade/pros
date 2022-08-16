"""automatic migration

Revision ID: afe80b6fd18b
Revises: 0754c3dbc090
Create Date: 2022-06-19 13:19:43.274864

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'afe80b6fd18b'
down_revision = '0754c3dbc090'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('railway_nodes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('coordinate', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # op.create_index('idx_railway_nodes_coordinate', 'railway_nodes', ['coordinate'], unique=False, postgresql_using='gist', postgresql_ops={})
    #op.drop_table('spatial_ref_sys')
    #op.add_column('projects_contents', sa.Column('bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cost', sa.Float(), nullable=True))
    #op.drop_column('projects_contents', 'bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
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
    op.drop_index('idx_railway_nodes_coordinate', table_name='railway_nodes', postgresql_using='gist', postgresql_ops={})
    op.drop_table('railway_nodes')
    # ### end Alembic commands ###
