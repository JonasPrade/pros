"""empty message

Revision ID: e1c90f473856
Revises: 6484c5eb20fc
Create Date: 2023-02-14 17:25:06.418167

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e1c90f473856'
down_revision = '6484c5eb20fc'
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
    op.drop_constraint('train_cycle_elements_train_cycle_id_fkey', 'train_cycle_elements', type_='foreignkey')
    op.create_foreign_key(None, 'train_cycle_elements', 'traincycles', ['train_cycle_id'], ['id'])
    op.create_foreign_key(None, 'train_cycle_elements', 'timetable_train', ['train_id'], ['id'])
    op.add_column('traincycles', sa.Column('trainline_id', sa.Integer(), nullable=True))
    op.add_column('traincycles', sa.Column('first_train_id', sa.String(length=510), nullable=True))
    op.drop_constraint('traingroup_traincycle_traingroup_id_wait_time_key', 'traincycles', type_='unique')
    op.create_unique_constraint('unique_traincycle', 'traincycles', ['trainline_id', 'wait_time', 'first_train_id'])
    op.drop_constraint('traingroup_traincycle_traingroup_id_fkey', 'traincycles', type_='foreignkey')
    op.create_foreign_key(None, 'traincycles', 'timetable_train', ['first_train_id'], ['id'])
    op.create_foreign_key(None, 'traincycles', 'timetable_lines', ['trainline_id'], ['id'])
    op.drop_column('traincycles', 'traingroup_id')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('traincycles', sa.Column('traingroup_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'traincycles', type_='foreignkey')
    op.drop_constraint(None, 'traincycles', type_='foreignkey')
    op.create_foreign_key('traingroup_traincycle_traingroup_id_fkey', 'traincycles', 'timetable_train_groups', ['traingroup_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    op.drop_constraint('unique_traincycle', 'traincycles', type_='unique')
    op.create_unique_constraint('traingroup_traincycle_traingroup_id_wait_time_key', 'traincycles', ['traingroup_id', 'wait_time'])
    op.drop_column('traincycles', 'first_train_id')
    op.drop_column('traincycles', 'trainline_id')
    op.drop_constraint(None, 'train_cycle_elements', type_='foreignkey')
    op.drop_constraint(None, 'train_cycle_elements', type_='foreignkey')
    op.create_foreign_key('train_cycle_elements_train_cycle_id_fkey', 'train_cycle_elements', 'traincycles', ['train_cycle_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
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
