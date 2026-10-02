"""dra_boq_measure_tables

Revision ID: 69826ec2d649
Revises: 51d03f0a7d37
Create Date: 2026-10-02 13:08:30.490695
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '69826ec2d649'
down_revision: Union[str, Sequence[str], None] = '51d03f0a7d37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('calculation_runs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('requested_by_user_id', sa.UUID(), nullable=True),
    sa.Column('rule_set_id', sa.UUID(), nullable=False),
    sa.Column('convention_code', sa.String(length=80), nullable=True),
    sa.Column('drawing_revision_ids', sa.ARRAY(sa.UUID()), server_default=sa.text("'{}'::uuid[]"), nullable=False),
    sa.Column('engine_version', sa.String(length=30), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='QUEUED', nullable=False),
    sa.Column('progress_pct', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_code', sa.String(length=60), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('QUEUED','RUNNING','STAGED','PROMOTED','COMPLETED','FAILED','CANCELLED','SUPERSEDED')", name='ck_calculation_runs_status'),
    sa.CheckConstraint('progress_pct >= 0 AND progress_pct <= 100', name='ck_calculation_runs_progress'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['rule_set_id'], ['measurement_rule_sets.id'], name='fk_calculation_runs_rule_set_id'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_calculation_runs_id_org')
    )
    op.create_index('ix_calculation_runs_org_project_status', 'calculation_runs', ['organization_id', 'project_id', 'status'], unique=False)
    op.create_index('uq_calculation_runs_active_project', 'calculation_runs', ['project_id'], unique=True, postgresql_where=sa.text("status IN ('QUEUED','RUNNING','STAGED','PROMOTED')"))
    op.create_index('uq_calculation_runs_completed_fingerprint', 'calculation_runs', ['organization_id', 'fingerprint'], unique=True, postgresql_where=sa.text("status = 'COMPLETED'"))
    op.create_table('run_stage_log',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('stage', sa.String(length=40), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
    sa.Column('attempt', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('counts', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','SKIPPED')", name='ck_run_stage_log_status'),
    sa.CheckConstraint('attempt >= 1', name='ck_run_stage_log_attempt'),
    sa.ForeignKeyConstraint(['run_id', 'organization_id'], ['calculation_runs.id', 'calculation_runs.organization_id'], name='fk_run_stage_log_run_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('run_id', 'stage', name='uq_run_stage_log_run_stage')
    )
    op.create_table('quantity_solids',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('element_id', sa.UUID(), nullable=True),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('component_type', sa.String(length=30), nullable=False),
    sa.Column('geometry_kind', sa.String(length=20), nullable=False),
    sa.Column('material_grade', sa.String(length=50), nullable=True),
    sa.Column('gross_volume_m3', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('gross_area_m2', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('gross_length_m', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='OK', nullable=False),
    sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('engine_version', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("geometry_kind IN ('EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED')", name='ck_quantity_solids_geometry_kind'),
    sa.CheckConstraint("status IN ('OK','REVIEW_REQUIRED','REJECTED')", name='ck_quantity_solids_status'),
    sa.CheckConstraint('(gross_volume_m3 IS NULL OR gross_volume_m3 >= 0) AND (gross_area_m2 IS NULL OR gross_area_m2 >= 0) AND (gross_length_m IS NULL OR gross_length_m >= 0) AND (count IS NULL OR count >= 0)', name='ck_quantity_solids_non_negative'),
    sa.ForeignKeyConstraint(['element_id'], ['drawing_elements.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['level_id'], ['building_levels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['run_id', 'organization_id'], ['calculation_runs.id', 'calculation_runs.organization_id'], name='fk_quantity_solids_run_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_quantity_solids_id_org'),
    sa.UniqueConstraint('run_id', 'element_id', 'component_type', name='uq_quantity_solids_run_element_component')
    )
    op.create_index('ix_quantity_solids_element', 'quantity_solids', ['element_id'], unique=False)
    op.create_index('ix_quantity_solids_run_level', 'quantity_solids', ['run_id', 'level_id'], unique=False)
    op.create_table('staged_quantity_solids',
    sa.Column('stage', sa.String(length=40), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('element_id', sa.UUID(), nullable=True),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('component_type', sa.String(length=30), nullable=False),
    sa.Column('geometry_kind', sa.String(length=20), nullable=False),
    sa.Column('material_grade', sa.String(length=50), nullable=True),
    sa.Column('gross_volume_m3', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('gross_area_m2', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('gross_length_m', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='OK', nullable=False),
    sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('engine_version', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("geometry_kind IN ('EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED')", name='ck_staged_quantity_solids_geometry_kind'),
    sa.CheckConstraint("status IN ('OK','REVIEW_REQUIRED','REJECTED')", name='ck_staged_quantity_solids_status'),
    sa.ForeignKeyConstraint(['element_id'], ['drawing_elements.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['level_id'], ['building_levels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['run_id', 'organization_id'], ['calculation_runs.id', 'calculation_runs.organization_id'], name='fk_staged_quantity_solids_run_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_staged_quantity_solids_id_org')
    )
    op.create_index('ix_staged_quantity_solids_run_stage', 'staged_quantity_solids', ['run_id', 'stage'], unique=False)
    op.create_table('quantity_ledger',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('solid_id', sa.UUID(), nullable=False),
    sa.Column('element_id', sa.UUID(), nullable=True),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('work_item_code', sa.String(length=50), nullable=False),
    sa.Column('quantity_net', sa.Numeric(precision=20, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('material_grade', sa.String(length=50), nullable=True),
    sa.Column('source_kind', sa.String(length=20), server_default='MODEL', nullable=False),
    sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('formula_code', sa.String(length=80), nullable=False),
    sa.Column('trace', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('engine_version', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source_kind IN ('MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE')", name='ck_quantity_ledger_source_kind'),
    sa.CheckConstraint("unit IN ('m3','m2','m','kg','nos')", name='ck_quantity_ledger_unit'),
    sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_quantity_ledger_confidence'),
    sa.CheckConstraint('quantity_net >= 0', name='ck_quantity_ledger_non_negative'),
    sa.ForeignKeyConstraint(['element_id'], ['drawing_elements.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['level_id'], ['building_levels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['run_id', 'organization_id'], ['calculation_runs.id', 'calculation_runs.organization_id'], name='fk_quantity_ledger_run_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['solid_id', 'organization_id'], ['quantity_solids.id', 'quantity_solids.organization_id'], name='fk_quantity_ledger_solid_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_quantity_ledger_id_org'),
    sa.UniqueConstraint('run_id', 'solid_id', 'work_item_code', name='uq_quantity_ledger_run_solid_work_item')
    )
    op.create_index('ix_quantity_ledger_run_solid', 'quantity_ledger', ['run_id', 'solid_id'], unique=False)
    op.create_index('ix_quantity_ledger_run_work_item_level', 'quantity_ledger', ['run_id', 'work_item_code', 'level_id'], unique=False)
    op.create_table('staged_quantity_ledger',
    sa.Column('stage', sa.String(length=40), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('solid_id', sa.UUID(), nullable=False),
    sa.Column('element_id', sa.UUID(), nullable=True),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('work_item_code', sa.String(length=50), nullable=False),
    sa.Column('quantity_net', sa.Numeric(precision=20, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('material_grade', sa.String(length=50), nullable=True),
    sa.Column('source_kind', sa.String(length=20), server_default='MODEL', nullable=False),
    sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('formula_code', sa.String(length=80), nullable=False),
    sa.Column('trace', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('engine_version', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("unit IN ('m3','m2','m','kg','nos')", name='ck_staged_quantity_ledger_unit'),
    sa.CheckConstraint('quantity_net >= 0', name='ck_staged_quantity_ledger_non_negative'),
    sa.ForeignKeyConstraint(['element_id'], ['drawing_elements.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['level_id'], ['building_levels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['run_id', 'organization_id'], ['calculation_runs.id', 'calculation_runs.organization_id'], name='fk_staged_quantity_ledger_run_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['solid_id', 'organization_id'], ['staged_quantity_solids.id', 'staged_quantity_solids.organization_id'], name='fk_staged_quantity_ledger_solid_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_staged_quantity_ledger_id_org'),
    sa.UniqueConstraint('run_id', 'solid_id', 'work_item_code', name='uq_staged_quantity_ledger_run_solid_work_item')
    )
    op.create_index('ix_staged_quantity_ledger_run_stage', 'staged_quantity_ledger', ['run_id', 'stage'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_staged_quantity_ledger_run_stage', table_name='staged_quantity_ledger')
    op.drop_table('staged_quantity_ledger')
    op.drop_index('ix_quantity_ledger_run_work_item_level', table_name='quantity_ledger')
    op.drop_index('ix_quantity_ledger_run_solid', table_name='quantity_ledger')
    op.drop_table('quantity_ledger')
    op.drop_index('ix_staged_quantity_solids_run_stage', table_name='staged_quantity_solids')
    op.drop_table('staged_quantity_solids')
    op.drop_index('ix_quantity_solids_run_level', table_name='quantity_solids')
    op.drop_index('ix_quantity_solids_element', table_name='quantity_solids')
    op.drop_table('quantity_solids')
    op.drop_table('run_stage_log')
    op.drop_index('uq_calculation_runs_completed_fingerprint', table_name='calculation_runs', postgresql_where=sa.text("status = 'COMPLETED'"))
    op.drop_index('uq_calculation_runs_active_project', table_name='calculation_runs', postgresql_where=sa.text("status IN ('QUEUED','RUNNING','STAGED','PROMOTED')"))
    op.drop_index('ix_calculation_runs_org_project_status', table_name='calculation_runs')
    op.drop_table('calculation_runs')