"""automatic migration

Revision ID: 45b0b02661b1
Revises: 49c3c4d6ac73
Create Date: 2022-09-11 19:13:23.508237

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '45b0b02661b1'
down_revision = '49c3c4d6ac73'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('spatial_ref_sys')
    op.add_column('vehicles_pattern', sa.Column('maintenance_cost_length_t', sa.Float(), nullable=True, comment='€/1000tkm'))
    op.add_column('vehicles_pattern', sa.Column('maintenance_cost_duration_t', sa.Float(), nullable=True, comment='€/(t*year)'))
    op.add_column('vehicles_pattern', sa.Column('energy_per_tkm', sa.Float(), nullable=True, comment='energy_unit/1000tkm'))
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('vehicles_pattern', 'energy_per_tkm')
    op.drop_column('vehicles_pattern', 'maintenance_cost_duration_t')
    op.drop_column('vehicles_pattern', 'maintenance_cost_length_t')
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
