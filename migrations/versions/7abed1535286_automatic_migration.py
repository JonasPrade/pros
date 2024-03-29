"""automatic migration

Revision ID: 7abed1535286
Revises: 7063c2e41f69
Create Date: 2022-06-13 20:33:01.153162

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision = '7abed1535286'
down_revision = '7063c2e41f69'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    #op.drop_table('spatial_ref_sys')
    op.add_column('constituencies', sa.Column('name', sa.String(length=255), nullable=False))
    op.add_column('constituencies', sa.Column('polygon', geoalchemy2.types.Geometry(srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))
    op.add_column('constituencies', sa.Column('state_id', sa.Integer(), nullable=True))
    # op.create_index('idx_constituencies_polygon', 'constituencies', ['polygon'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_foreign_key(None, 'constituencies', 'states', ['state_id'], ['id'])
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'constituencies', type_='foreignkey')
    op.drop_index('idx_constituencies_polygon', table_name='constituencies', postgresql_using='gist', postgresql_ops={})
    op.drop_column('constituencies', 'state_id')
    op.drop_column('constituencies', 'polygon')
    op.drop_column('constituencies', 'name')
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

