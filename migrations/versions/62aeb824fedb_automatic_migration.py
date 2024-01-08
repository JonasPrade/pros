"""automatic migration

Revision ID: 62aeb824fedb
Revises: 7c3eb584917f
Create Date: 2023-12-15 18:42:39.094302

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62aeb824fedb'
down_revision = '7c3eb584917f'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('spatial_ref_sys')
    op.add_column('budgets', sa.Column('cost_estimate_actual_861_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_861_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_861_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues_861_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_861_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_861_01', sa.Integer(), nullable=True))
    op.add_column('finve', sa.Column('temporary_finve_number', sa.Boolean(), nullable=True))
    op.alter_column('finve_to_projectcontent', 'finve_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('finve_to_projectcontent', 'pc_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('finve_to_projectcontent', 'pc_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('finve_to_projectcontent', 'finve_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_column('finve', 'temporary_finve_number')
    op.drop_column('budgets', 'next_years_861_01')
    op.drop_column('budgets', 'year_planned_861_01')
    op.drop_column('budgets', 'spending_residues_861_01')
    op.drop_column('budgets', 'allowed_previous_year_861_01')
    op.drop_column('budgets', 'spent_two_years_previous_861_01')
    op.drop_column('budgets', 'cost_estimate_actual_861_01')
    # op.create_table('spatial_ref_sys',
    # sa.Column('srid', sa.INTEGER(), autoincrement=False, nullable=False),
    # sa.Column('auth_name', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
    # sa.Column('auth_srid', sa.INTEGER(), autoincrement=False, nullable=True),
    # sa.Column('srtext', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    # sa.Column('proj4text', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    # sa.CheckConstraint('(srid > 0) AND (srid <= 998999)', name='spatial_ref_sys_srid_check'),
    # sa.PrimaryKeyConstraint('srid', name='spatial_ref_sys_pkey')
    # )
    # ### end Alembic commands ###

