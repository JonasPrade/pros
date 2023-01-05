"""empty message

Revision ID: b245aeb7d609
Revises: 8004ada40c23
Create Date: 2022-12-30 15:57:48.872395

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b245aeb7d609'
down_revision = '8004ada40c23'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('master_scenarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('start_year', sa.Integer(), nullable=True),
    sa.Column('operation_duration', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('master_areas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scenario_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['scenario_id'], ['master_scenarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pc_to_masterareas',
    sa.Column('projectcontent_id', sa.Integer(), nullable=True),
    sa.Column('masterarea_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['masterarea_id'], ['master_areas.id'], ),
    sa.ForeignKeyConstraint(['projectcontent_id'], ['projects_contents.id'], )
    )
    op.create_table('rwl_to_masterareas',
    sa.Column('railwayline_id', sa.Integer(), nullable=True),
    sa.Column('masterarea_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['masterarea_id'], ['master_areas.id'], ),
    sa.ForeignKeyConstraint(['railwayline_id'], ['railway_lines.id'], )
    )
    op.create_table('tg_to_masterareas',
    sa.Column('traingroup_id', sa.String(length=255), nullable=True),
    sa.Column('masterarea_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['masterarea_id'], ['master_areas.id'], ),
    sa.ForeignKeyConstraint(['traingroup_id'], ['timetable_train_groups.id'], )
    )
    # op.drop_table('spatial_ref_sys')
    # op.drop_index('budgets_year_and_finve_uindex', table_name='budgets')
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
    op.drop_table('tg_to_masterareas')
    op.drop_table('rwl_to_masterareas')
    op.drop_table('pc_to_masterareas')
    op.drop_table('master_areas')
    op.drop_table('master_scenarios')
    # ### end Alembic commands ###

