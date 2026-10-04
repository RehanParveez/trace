"""finishes and schedules

Revision ID: 1fce406782ae
Revises: 89c250998e81
Create Date: 2026-10-04 14:36:55.345499
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1fce406782ae'
down_revision: Union[str, Sequence[str], None] = '89c250998e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_unique_constraint(
        'uq_drawings_id_org',
        'drawings',
        ['id', 'organization_id'],
    )

    op.create_unique_constraint(
        'uq_drawing_elements_id_org',
        'drawing_elements',
        ['id', 'organization_id'],
    )

    op.create_table('finish_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('rule_set_id', sa.UUID(), nullable=False),
    sa.Column('space_category', sa.String(length=40), server_default='ALL', nullable=False),
    sa.Column('surface', sa.String(length=12), nullable=False),
    sa.Column('work_item_code', sa.String(length=50), nullable=False),
    sa.Column('height_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('deduct_openings', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('priority', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('extra_config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("surface IN ('FLOOR','WALL','CEILING','SKIRTING','DADO')", name='ck_finish_rules_surface'),
    sa.CheckConstraint('height_mm IS NULL OR height_mm > 0', name='ck_finish_rules_height'),
    sa.ForeignKeyConstraint(['rule_set_id'], ['measurement_rule_sets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rule_set_id', 'space_category', 'surface', 'work_item_code', name='uq_finish_rules_scope_surface_item')
    )

    op.create_index('ix_finish_rules_rule_set', 'finish_rules', ['rule_set_id'], unique=False)
    op.create_table('schedule_imports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('drawing_id', sa.UUID(), nullable=True),
    sa.Column('source', sa.String(length=12), nullable=False),
    sa.Column('schedule_kind', sa.String(length=12), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='PENDING_REVIEW', nullable=False),
    sa.Column('file_name', sa.String(length=500), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('row_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('confirmed_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('extraction_meta', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('confirmed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("schedule_kind IN ('DOOR','WINDOW','FINISH','FIXTURE','GENERAL')", name='ck_schedule_imports_kind'),
    sa.CheckConstraint("source IN ('PDF_AI','PDF_TEXT','CSV','MANUAL')", name='ck_schedule_imports_source'),
    sa.CheckConstraint("status IN ('PENDING_REVIEW','CONFIRMED','REJECTED','ARCHIVED')", name='ck_schedule_imports_status'),
    sa.CheckConstraint('row_count >= 0 AND confirmed_count >= 0 AND confirmed_count <= row_count', name='ck_schedule_imports_counts'),
    sa.ForeignKeyConstraint(['confirmed_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['drawing_id'], ['drawings.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_schedule_imports_id_org')
    )

    op.create_index('ix_schedule_imports_org_project', 'schedule_imports', ['organization_id', 'project_id'], unique=False)
    op.create_index('uq_schedule_imports_project_hash', 'schedule_imports', ['project_id', 'content_hash'], unique=True, postgresql_where=sa.text("content_hash IS NOT NULL AND status IN ('PENDING_REVIEW','CONFIRMED')"))
    op.create_table('building_spaces',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('drawing_id', sa.UUID(), nullable=True),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('source', sa.String(length=10), server_default='IFC', nullable=False),
    sa.Column('ifc_global_id', sa.String(length=64), nullable=True),
    sa.Column('number', sa.String(length=100), nullable=True),
    sa.Column('name', sa.String(length=300), nullable=True),
    sa.Column('long_name', sa.String(length=500), nullable=True),
    sa.Column('category', sa.String(length=40), server_default='UNKNOWN', nullable=False),
    sa.Column('usage_text', sa.String(length=300), nullable=True),
    sa.Column('is_external', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('gross_floor_area_mm2', sa.Numeric(precision=20, scale=3), nullable=True),
    sa.Column('net_floor_area_mm2', sa.Numeric(precision=20, scale=3), nullable=True),
    sa.Column('perimeter_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('height_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('elevation_base_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('geometry_kind', sa.String(length=20), server_default='UNSUPPORTED', nullable=False),
    sa.Column('footprint', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('normalization_status', sa.String(length=10), server_default='VALID', nullable=False),
    sa.Column('normalization_issues', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("geometry_kind IN ('EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED')", name='ck_building_spaces_geometry_kind'),
    sa.CheckConstraint("normalization_status IN ('PENDING','VALID','WARNING','INVALID')", name='ck_building_spaces_normalization_status'),
    sa.CheckConstraint("source <> 'IFC' OR drawing_id IS NOT NULL", name='ck_building_spaces_ifc_has_drawing'),
    sa.CheckConstraint("source IN ('IFC','MANUAL')", name='ck_building_spaces_source'),
    sa.CheckConstraint('(gross_floor_area_mm2 IS NULL OR gross_floor_area_mm2 >= 0) AND (net_floor_area_mm2 IS NULL OR net_floor_area_mm2 >= 0) AND (perimeter_mm IS NULL OR perimeter_mm >= 0) AND (height_mm IS NULL OR height_mm >= 0)', name='ck_building_spaces_non_negative'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_building_spaces_drawing_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['level_id'], ['building_levels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('drawing_id', 'ifc_global_id', name='uq_building_spaces_drawing_global_id'),
    sa.UniqueConstraint('id', 'organization_id', name='uq_building_spaces_id_org')
    )
    op.create_index('ix_building_spaces_drawing_level', 'building_spaces', ['drawing_id', 'level_id'], unique=False)
    op.create_index('ix_building_spaces_org_project', 'building_spaces', ['organization_id', 'project_id'], unique=False)
    op.create_table('element_relations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('drawing_id', sa.UUID(), nullable=False),
    sa.Column('from_element_id', sa.UUID(), nullable=False),
    sa.Column('to_element_id', sa.UUID(), nullable=False),
    sa.Column('relation', sa.String(length=12), nullable=False),
    sa.Column('source', sa.String(length=10), server_default='IFC', nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("relation IN ('HOSTED_IN','SUPPORTS','CONNECTS','ADJACENT')", name='ck_element_relations_relation'),
    sa.CheckConstraint("source IN ('IFC','DERIVED')", name='ck_element_relations_source'),
    sa.CheckConstraint('from_element_id <> to_element_id', name='ck_element_relations_distinct'),
    sa.ForeignKeyConstraint(['drawing_id', 'organization_id'], ['drawings.id', 'drawings.organization_id'], name='fk_element_relations_drawing_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['from_element_id', 'organization_id'], ['drawing_elements.id', 'drawing_elements.organization_id'], name='fk_element_relations_from_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_element_id', 'organization_id'], ['drawing_elements.id', 'drawing_elements.organization_id'], name='fk_element_relations_to_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('from_element_id', 'to_element_id', 'relation', name='uq_element_relations_pair_kind')
    )

    op.create_index('ix_element_relations_drawing_relation', 'element_relations', ['drawing_id', 'relation'], unique=False)
    op.create_index('ix_element_relations_to_element', 'element_relations', ['to_element_id'], unique=False)
    op.create_table('schedule_rows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('schedule_import_id', sa.UUID(), nullable=False),
    sa.Column('row_no', sa.Integer(), nullable=False),
    sa.Column('schedule_kind', sa.String(length=12), nullable=False),
    sa.Column('page_no', sa.Integer(), nullable=True),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('mark', sa.String(length=100), nullable=True),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('location_text', sa.String(length=300), nullable=True),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('space_id', sa.UUID(), nullable=True),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('width_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('height_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('work_item_code', sa.String(length=50), nullable=True),
    sa.Column('canonical_unit', sa.String(length=20), nullable=True),
    sa.Column('canonical_quantity', sa.Numeric(precision=20, scale=6), nullable=True),
    sa.Column('confidence', sa.Numeric(precision=5, scale=4), server_default='0.5', nullable=False),
    sa.Column('review_status', sa.String(length=10), server_default='PENDING', nullable=False),
    sa.Column('review_note', sa.Text(), nullable=True),
    sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('matched_element_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("canonical_unit IS NULL OR canonical_unit IN ('m3','m2','m','kg','nos')", name='ck_schedule_rows_canonical_unit'),
    sa.CheckConstraint("review_status <> 'CONFIRMED' OR (work_item_code IS NOT NULL AND canonical_unit IS NOT NULL AND canonical_quantity IS NOT NULL)", name='ck_schedule_rows_confirmed_is_mapped'),
    sa.CheckConstraint("review_status IN ('PENDING','CONFIRMED','REJECTED')", name='ck_schedule_rows_review_status'),
    sa.CheckConstraint("schedule_kind IN ('DOOR','WINDOW','FINISH','FIXTURE','GENERAL')", name='ck_schedule_rows_kind'),
    sa.CheckConstraint('(quantity IS NULL OR quantity >= 0) AND (canonical_quantity IS NULL OR canonical_quantity >= 0)', name='ck_schedule_rows_non_negative'),
    sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_schedule_rows_confidence'),
    sa.CheckConstraint('row_no >= 1', name='ck_schedule_rows_row_no'),
    sa.ForeignKeyConstraint(['level_id'], ['building_levels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['schedule_import_id', 'organization_id'], ['schedule_imports.id', 'schedule_imports.organization_id'], name='fk_schedule_rows_import_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['space_id'], ['building_spaces.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('schedule_import_id', 'row_no', name='uq_schedule_rows_import_row')
    )
    op.create_index('ix_schedule_rows_import', 'schedule_rows', ['schedule_import_id'], unique=False)
    op.create_index('ix_schedule_rows_org_status', 'schedule_rows', ['organization_id', 'review_status'], unique=False)
    op.create_table('space_boundaries',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('space_id', sa.UUID(), nullable=False),
    sa.Column('element_id', sa.UUID(), nullable=False),
    sa.Column('boundary_kind', sa.String(length=10), server_default='PHYSICAL', nullable=False),
    sa.Column('side', sa.String(length=10), server_default='UNDEFINED', nullable=False),
    sa.Column('source', sa.String(length=10), server_default='IFC', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("boundary_kind IN ('PHYSICAL','VIRTUAL')", name='ck_space_boundaries_kind'),
    sa.CheckConstraint("side IN ('INTERNAL','EXTERNAL','UNDEFINED')", name='ck_space_boundaries_side'),
    sa.CheckConstraint("source IN ('IFC','DERIVED')", name='ck_space_boundaries_source'),
    sa.ForeignKeyConstraint(['element_id', 'organization_id'], ['drawing_elements.id', 'drawing_elements.organization_id'], name='fk_space_boundaries_element_tenant', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['space_id', 'organization_id'], ['building_spaces.id', 'building_spaces.organization_id'], name='fk_space_boundaries_space_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('space_id', 'element_id', name='uq_space_boundaries_space_element')

    )

    op.create_index('ix_space_boundaries_element', 'space_boundaries', ['element_id'], unique=False)
    op.create_table('space_finishes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('space_id', sa.UUID(), nullable=False),
    sa.Column('surface', sa.String(length=12), nullable=False),
    sa.Column('work_item_code', sa.String(length=50), nullable=False),
    sa.Column('finish_name', sa.String(length=200), nullable=True),
    sa.Column('height_mm', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('source', sa.String(length=20), server_default='MANUAL', nullable=False),
    sa.Column('schedule_row_id', sa.UUID(), nullable=True),
    sa.Column('confidence', sa.Numeric(precision=5, scale=4), server_default='1', nullable=False),
    sa.Column('review_status', sa.String(length=20), server_default='OK', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("review_status IN ('OK','REVIEW_REQUIRED')", name='ck_space_finishes_review_status'),
    sa.CheckConstraint("source IN ('IFC_PSET','SCHEDULE_IMPORT','MANUAL','RULE_DEFAULT')", name='ck_space_finishes_source'),
    sa.CheckConstraint("surface IN ('FLOOR','WALL','CEILING','SKIRTING','DADO')", name='ck_space_finishes_surface'),
    sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_space_finishes_confidence'),
    sa.CheckConstraint('height_mm IS NULL OR height_mm > 0', name='ck_space_finishes_height'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['schedule_row_id'], ['schedule_rows.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['space_id', 'organization_id'], ['building_spaces.id', 'building_spaces.organization_id'], name='fk_space_finishes_space_tenant', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('space_id', 'surface', 'work_item_code', name='uq_space_finishes_space_surface_work_item')
    )
    op.create_index('ix_space_finishes_space', 'space_finishes', ['space_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_space_finishes_space', table_name='space_finishes')
    op.drop_table('space_finishes')
    op.drop_index('ix_space_boundaries_element', table_name='space_boundaries')
    op.drop_table('space_boundaries')
    op.drop_index('ix_schedule_rows_org_status', table_name='schedule_rows')
    op.drop_index('ix_schedule_rows_import', table_name='schedule_rows')
    op.drop_table('schedule_rows')
    op.drop_index('ix_element_relations_to_element', table_name='element_relations')
    op.drop_index('ix_element_relations_drawing_relation', table_name='element_relations')
    op.drop_table('element_relations')
    op.drop_index('ix_building_spaces_org_project', table_name='building_spaces')
    op.drop_index('ix_building_spaces_drawing_level', table_name='building_spaces')
    op.drop_table('building_spaces')
    op.drop_index('uq_schedule_imports_project_hash', table_name='schedule_imports', postgresql_where=sa.text("content_hash IS NOT NULL AND status IN ('PENDING_REVIEW','CONFIRMED')"))
    op.drop_index('ix_schedule_imports_org_project', table_name='schedule_imports')
    op.drop_table('schedule_imports')
    op.drop_index('ix_finish_rules_rule_set', table_name='finish_rules')
    op.drop_table('finish_rules')
    op.drop_constraint(
        'uq_drawing_elements_id_org',
        'drawing_elements',
        type_='unique',
    )
    op.drop_constraint(
        'uq_drawings_id_org',
        'drawings',
        type_='unique',
    )