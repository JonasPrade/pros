"""automatic migration

Revision ID: c9d22681817b
Revises: d332db131cf5
Create Date: 2022-09-30 11:10:05.216243

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9d22681817b'
down_revision = 'd332db131cf5'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('finve',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=1000), nullable=True),
    sa.Column('starting_year', sa.Integer(), nullable=True),
    sa.Column('cost_estimate_original', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('finve_to_projectcontent',
    sa.Column('finve_id', sa.Integer(), nullable=True),
    sa.Column('pc_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['finve_id'], ['finve.id'], ),
    sa.ForeignKeyConstraint(['pc_id'], ['projects_contents.id'], )
    )
    # op.drop_table('spatial_ref_sys')
    op.add_column('budgets', sa.Column('budget_year', sa.Integer(), nullable=False))
    op.add_column('budgets', sa.Column('lfd_nr', sa.String(length=100), nullable=True))
    op.add_column('budgets', sa.Column('fin_ve', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('bedarfsplan_number', sa.String(length=100), nullable=True))
    op.add_column('budgets', sa.Column('starting_year', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_original', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_last_year', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_third_parties', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_equity', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_891_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_891_02', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_891_03', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_891_04', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('cost_estimate_actual_891_91', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('delta_previous_year', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('delta_previous_year_relativ', sa.Float(), nullable=True))
    op.add_column('budgets', sa.Column('delta_previous_year_reasons', sa.Text(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_third_parties', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_equity', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_891_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_891_02', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_891_03', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_891_04', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spent_two_years_previous_891_91', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_third_parties', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_equity', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_891_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_891_02', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_891_03', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_891_04', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('allowed_previous_year_891_91', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues_891_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues_891_02', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues_891_03', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues_891_04', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('spending_residues_891_91', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_third_parties', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_equity', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_891_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_891_02', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_891_03', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_891_04', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('year_planned_891_91', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_third_parties', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_equity', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_891_01', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_891_02', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_891_03', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_891_04', sa.Integer(), nullable=True))
    op.add_column('budgets', sa.Column('next_years_891_91', sa.Integer(), nullable=True))
    op.drop_constraint('budgets_project_content_id_fkey', 'budgets', type_='foreignkey')
    op.create_foreign_key(None, 'budgets', 'finve', ['fin_ve'], ['id'])
    op.drop_column('budgets', 'planned_cost_this_year')
    op.drop_column('budgets', 'planned_cost_following_years')
    op.drop_column('budgets', 'spent_cost_two_years_before')
    op.drop_column('budgets', 'planned_cost_next_year')
    op.drop_column('budgets', 'delegated_costs')
    op.drop_column('budgets', 'year')
    op.drop_column('budgets', 'name')
    op.drop_column('budgets', 'allowed_year_before')
    op.drop_column('budgets', 'project_content_id')
    op.drop_column('budgets', 'type')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('budgets', sa.Column('type', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('project_content_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('allowed_year_before', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('year', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('delegated_costs', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('planned_cost_next_year', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('spent_cost_two_years_before', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('planned_cost_following_years', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('budgets', sa.Column('planned_cost_this_year', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'budgets', type_='foreignkey')
    op.create_foreign_key('budgets_project_content_id_fkey', 'budgets', 'projects_contents', ['project_content_id'], ['id'])
    op.drop_column('budgets', 'next_years_891_91')
    op.drop_column('budgets', 'next_years_891_04')
    op.drop_column('budgets', 'next_years_891_03')
    op.drop_column('budgets', 'next_years_891_02')
    op.drop_column('budgets', 'next_years_891_01')
    op.drop_column('budgets', 'next_years_equity')
    op.drop_column('budgets', 'next_years_third_parties')
    op.drop_column('budgets', 'next_years')
    op.drop_column('budgets', 'year_planned_891_91')
    op.drop_column('budgets', 'year_planned_891_04')
    op.drop_column('budgets', 'year_planned_891_03')
    op.drop_column('budgets', 'year_planned_891_02')
    op.drop_column('budgets', 'year_planned_891_01')
    op.drop_column('budgets', 'year_planned_equity')
    op.drop_column('budgets', 'year_planned_third_parties')
    op.drop_column('budgets', 'year_planned')
    op.drop_column('budgets', 'spending_residues_891_91')
    op.drop_column('budgets', 'spending_residues_891_04')
    op.drop_column('budgets', 'spending_residues_891_03')
    op.drop_column('budgets', 'spending_residues_891_02')
    op.drop_column('budgets', 'spending_residues_891_01')
    op.drop_column('budgets', 'spending_residues')
    op.drop_column('budgets', 'allowed_previous_year_891_91')
    op.drop_column('budgets', 'allowed_previous_year_891_04')
    op.drop_column('budgets', 'allowed_previous_year_891_03')
    op.drop_column('budgets', 'allowed_previous_year_891_02')
    op.drop_column('budgets', 'allowed_previous_year_891_01')
    op.drop_column('budgets', 'allowed_previous_year_equity')
    op.drop_column('budgets', 'allowed_previous_year_third_parties')
    op.drop_column('budgets', 'allowed_previous_year')
    op.drop_column('budgets', 'spent_two_years_previous_891_91')
    op.drop_column('budgets', 'spent_two_years_previous_891_04')
    op.drop_column('budgets', 'spent_two_years_previous_891_03')
    op.drop_column('budgets', 'spent_two_years_previous_891_02')
    op.drop_column('budgets', 'spent_two_years_previous_891_01')
    op.drop_column('budgets', 'spent_two_years_previous_equity')
    op.drop_column('budgets', 'spent_two_years_previous_third_parties')
    op.drop_column('budgets', 'spent_two_years_previous')
    op.drop_column('budgets', 'delta_previous_year_reasons')
    op.drop_column('budgets', 'delta_previous_year_relativ')
    op.drop_column('budgets', 'delta_previous_year')
    op.drop_column('budgets', 'cost_estimate_actual_891_91')
    op.drop_column('budgets', 'cost_estimate_actual_891_04')
    op.drop_column('budgets', 'cost_estimate_actual_891_03')
    op.drop_column('budgets', 'cost_estimate_actual_891_02')
    op.drop_column('budgets', 'cost_estimate_actual_891_01')
    op.drop_column('budgets', 'cost_estimate_actual_equity')
    op.drop_column('budgets', 'cost_estimate_actual_third_parties')
    op.drop_column('budgets', 'cost_estimate_actual')
    op.drop_column('budgets', 'cost_estimate_last_year')
    op.drop_column('budgets', 'cost_estimate_original')
    op.drop_column('budgets', 'starting_year')
    op.drop_column('budgets', 'bedarfsplan_number')
    op.drop_column('budgets', 'fin_ve')
    op.drop_column('budgets', 'lfd_nr')
    op.drop_column('budgets', 'budget_year')
    op.create_table('spatial_ref_sys',
    sa.Column('srid', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('auth_name', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
    sa.Column('auth_srid', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('srtext', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.Column('proj4text', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.CheckConstraint('(srid > 0) AND (srid <= 998999)', name='spatial_ref_sys_srid_check'),
    sa.PrimaryKeyConstraint('srid', name='spatial_ref_sys_pkey')
    )
    op.drop_table('finve_to_projectcontent')
    op.drop_table('finve')
    # ### end Alembic commands ###

