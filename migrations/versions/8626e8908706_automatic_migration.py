"""automatic migration

Revision ID: 8626e8908706
Revises: cec8262b027e
Create Date: 2024-01-18 22:13:05.763612

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8626e8908706'
down_revision = 'cec8262b027e'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('spatial_ref_sys')
    op.add_column('netzzustandsbericht', sa.Column('replacement_value_support_structure', sa.Float(), nullable=True, comment='Wiederbeschaffungswert Stützbauwerke Mrd. €'))
    op.add_column('netzzustandsbericht', sa.Column('replacement_value_corrected_all', sa.Float(), nullable=True, comment='Wiederbeschaffungswert gesamt Mrd. €'))
    op.add_column('netzzustandsbericht', sa.Column('replacement_value_corrected_support_structure', sa.Float(), nullable=True, comment='Wiederbeschaffungswert Stützbauwerke Mrd. €'))
    op.add_column('netzzustandsbericht', sa.Column('replacement_distribution_all', sa.Float(), nullable=True, comment='Wiederbeschaffungswert gesamt %'))
    op.add_column('netzzustandsbericht', sa.Column('replacement_distribution_support_structure', sa.Float(), nullable=True, comment='Wiederbeschaffungswert Stützbauwerke %'))
    op.drop_column('netzzustandsbericht', 'replacment_value_support_structure')
    op.drop_column('netzzustandsbericht', 'replacment_value_corrected_all')
    op.drop_column('netzzustandsbericht', 'replacment_value_corrected_support_structure')
    op.drop_column('netzzustandsbericht', 'replacment_distribution_all')
    op.drop_column('netzzustandsbericht', 'replacment_distribution_support_structure')
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('netzzustandsbericht', sa.Column('replacment_distribution_support_structure', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True, comment='Wiederbeschaffungswert Stützbauwerke %'))
    op.add_column('netzzustandsbericht', sa.Column('replacment_distribution_all', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True, comment='Wiederbeschaffungswert gesamt %'))
    op.add_column('netzzustandsbericht', sa.Column('replacment_value_corrected_support_structure', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True, comment='Wiederbeschaffungswert Stützbauwerke Mrd. €'))
    op.add_column('netzzustandsbericht', sa.Column('replacment_value_corrected_all', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True, comment='Wiederbeschaffungswert gesamt Mrd. €'))
    op.add_column('netzzustandsbericht', sa.Column('replacment_value_support_structure', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True, comment='Wiederbeschaffungswert Stützbauwerke Mrd. €'))
    op.drop_column('netzzustandsbericht', 'replacement_distribution_support_structure')
    op.drop_column('netzzustandsbericht', 'replacement_distribution_all')
    op.drop_column('netzzustandsbericht', 'replacement_value_corrected_support_structure')
    op.drop_column('netzzustandsbericht', 'replacement_value_corrected_all')
    op.drop_column('netzzustandsbericht', 'replacement_value_support_structure')
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

