"""empty message

Revision ID: 31853c5d4123
Revises: f02469156110
Create Date: 2023-06-07 16:30:28.710311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '31853c5d4123'
down_revision = 'f02469156110'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('spatial_ref_sys')
    op.add_column('texts', sa.Column('header', sa.String(length=1000), nullable=True))
    op.add_column('texts', sa.Column('weblink', sa.String(length=1000), nullable=True))
    op.add_column('texts', sa.Column('text', sa.Text(), nullable=True))
    op.drop_column('texts', 'content')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('texts', sa.Column('content', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_column('texts', 'text')
    op.drop_column('texts', 'weblink')
    op.drop_column('texts', 'header')
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

