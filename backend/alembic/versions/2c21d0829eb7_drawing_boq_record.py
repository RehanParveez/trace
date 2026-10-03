"""boq from ledger 

Revision ID: 2c21d0829eb7
Revises: 5db4f7917cd6
Create Date: 2026-10-03 16:40:40.461999
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2c21d0829eb7"
down_revision: Union[str, Sequence[str], None] = "5db4f7917cd6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list:
  return [
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
  ]

def upgrade() -> None:
    op.create_unique_constraint("uq_boq_versions_id_org", "boq_versions", ["id", "organization_id"])
    op.create_unique_constraint("uq_boq_items_id_org", "boq_items", ["id", "organization_id"])
    
    op.add_column("boq_versions", sa.Column("lifecycle", sa.String(length=20), server_default="DRAFT", nullable=False))
    op.add_column("boq_versions", sa.Column("origin", sa.String(length=10), server_default="LEGACY", nullable=False))
    op.add_column("boq_versions", sa.Column("calculation_run_id", sa.UUID(), nullable=True))
    op.add_column("boq_versions", sa.Column("snapshot_id", sa.UUID(), nullable=True))
    op.add_column("boq_versions", sa.Column("approved_by_user_id", sa.UUID(), nullable=True))
    op.add_column("boq_versions", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("boq_versions", sa.Column("issued_by_user_id", sa.UUID(), nullable=True))
    op.add_column("boq_versions", sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("boq_items", sa.Column("item_key", sa.String(length=300), nullable=True))
    op.add_column("boq_items", sa.Column("level_id", sa.UUID(), nullable=True))
    op.add_column("boq_items", sa.Column("material_grade", sa.String(length=50), nullable=True))
    op.add_column("boq_items", sa.Column("canonical_unit", sa.String(length=20), nullable=True))
    op.add_column("boq_items", sa.Column("unit_factor", sa.Numeric(precision=20, scale=10), nullable=True))
    op.add_column("boq_items", sa.Column("adjustment_total", sa.Numeric(precision=18, scale=4), server_default=sa.text("0"), nullable=False))
    op.add_column("boq_items", sa.Column("review_status", sa.String(length=20), server_default="OK", nullable=False))
    op.add_column("boq_items", sa.Column("source_kind", sa.String(length=20), server_default="LEGACY", nullable=False))
    op.add_column("boq_items", sa.Column("is_manual", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("boq_items", sa.Column("calculation_run_id", sa.UUID(), nullable=True))
    op.add_column("boq_items", sa.Column("engine_version", sa.String(length=30), nullable=True))

    op.create_table(
        "boq_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("boq_version_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=10), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("totals", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("calculation_run_id", sa.UUID(), nullable=True),
        sa.Column("rule_set_id", sa.UUID(), nullable=True),
        sa.Column("rule_set_code", sa.String(length=50), nullable=True),
        sa.Column("rule_set_version", sa.Integer(), nullable=True),
        sa.Column("convention_code", sa.String(length=80), nullable=True),
        sa.Column("engine_version", sa.String(length=30), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("purpose IN ('APPROVAL','ISSUE','MANUAL')", name="ck_boq_snapshots_purpose"),
        sa.CheckConstraint("char_length(content_hash) = 64", name="ck_boq_snapshots_hash_len"),
        sa.CheckConstraint("item_count >= 0", name="ck_boq_snapshots_item_count"),
        sa.CheckConstraint("version_no >= 1", name="ck_boq_snapshots_version_no"),
        sa.ForeignKeyConstraint(["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"], name="fk_boq_snapshots_version_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["calculation_run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"], name="fk_boq_snapshots_run_tenant"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_boq_snapshots_created_by", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rule_set_id"], ["measurement_rule_sets.id"], name="fk_boq_snapshots_rule_set_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("boq_version_id", "version_no", name="uq_boq_snapshots_version_no"),
        sa.UniqueConstraint("id", "organization_id", name="uq_boq_snapshots_id_org"),
    )
    op.create_index("ix_boq_snapshots_version", "boq_snapshots", ["boq_version_id"], unique=False)

    op.create_table(
        "boq_item_adjustments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("boq_item_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.UUID(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("kind <> 'REPLACE' OR value >= 0", name="ck_boq_item_adjustments_replace_non_negative"),
        sa.CheckConstraint("kind IN ('DELTA','REPLACE')", name="ck_boq_item_adjustments_kind"),
        sa.CheckConstraint("char_length(btrim(reason)) > 0", name="ck_boq_item_adjustments_reason"),
        sa.ForeignKeyConstraint(["boq_item_id", "organization_id"], ["boq_items.id", "boq_items.organization_id"], name="fk_boq_item_adjustments_item_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_boq_item_adjustments_created_by", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], name="fk_boq_item_adjustments_revoked_by", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_boq_item_adjustments_id_org"),
    )
    op.create_index("ix_boq_item_adjustments_item", "boq_item_adjustments", ["boq_item_id"], unique=False)
    op.create_index(
        "uq_boq_item_adjustments_active_replace", "boq_item_adjustments", ["boq_item_id"],
        unique=True, postgresql_where=sa.text("kind = 'REPLACE' AND revoked_at IS NULL"),
    )

    op.create_table(
        "boq_snapshot_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("source_item_id", sa.UUID(), nullable=True),
        sa.Column("item_key", sa.String(length=300), nullable=True),
        sa.Column("work_item_code", sa.String(length=50), nullable=True),
        sa.Column("material_name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=150), nullable=True),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("level_id", sa.UUID(), nullable=True),
        sa.Column("material_grade", sa.String(length=50), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("canonical_unit", sa.String(length=20), nullable=True),
        sa.Column("unit_factor", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("net_quantity", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("adjustment_total", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("waste_factor_applied", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("gross_quantity", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("unit_rate", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("rate_source", sa.String(length=20), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("source_kind", sa.String(length=20), nullable=False),
        sa.Column("is_manual", sa.Boolean(), nullable=False),
        sa.Column("ledger_row_count", sa.Integer(), nullable=False),
        sa.Column("ledger_hash", sa.String(length=64), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("line_no >= 1", name="ck_boq_snapshot_items_line_no"),
        sa.ForeignKeyConstraint(["snapshot_id", "organization_id"], ["boq_snapshots.id", "boq_snapshots.organization_id"], name="fk_boq_snapshot_items_snapshot_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "line_no", name="uq_boq_snapshot_items_line"),
    )
    op.create_index("ix_boq_snapshot_items_snapshot", "boq_snapshot_items", ["snapshot_id"], unique=False)
    op.create_index("ix_boq_snapshot_items_source", "boq_snapshot_items", ["source_item_id"], unique=False)

    op.create_table(
        "boq_item_ledger_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("boq_version_id", sa.UUID(), nullable=False),
        sa.Column("boq_item_id", sa.UUID(), nullable=False),
        sa.Column("ledger_id", sa.UUID(), nullable=False),
        sa.Column("quantity_contributed", sa.Numeric(precision=20, scale=6), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("quantity_contributed >= 0", name="ck_boq_item_ledger_links_non_negative"),
        sa.ForeignKeyConstraint(["boq_item_id", "organization_id"], ["boq_items.id", "boq_items.organization_id"], name="fk_boq_item_ledger_links_item_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"], name="fk_boq_item_ledger_links_version_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ledger_id", "organization_id"], ["quantity_ledger.id", "quantity_ledger.organization_id"], name="fk_boq_item_ledger_links_ledger_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("boq_item_id", "ledger_id", name="uq_boq_item_ledger_links_item_ledger"),
        sa.UniqueConstraint("boq_version_id", "ledger_id", name="uq_boq_item_ledger_links_version_ledger"),
    )
    op.create_index("ix_boq_item_ledger_links_ledger", "boq_item_ledger_links", ["ledger_id"], unique=False)

    op.create_table(
        "review_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("boq_version_id", sa.UUID(), nullable=True),
        sa.Column("calculation_run_id", sa.UUID(), nullable=True),
        sa.Column("drawing_element_id", sa.UUID(), nullable=True),
        sa.Column("ledger_id", sa.UUID(), nullable=True),
        sa.Column("boq_item_id", sa.UUID(), nullable=True),
        sa.Column("adjustment_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("blocks", sa.String(length=10), server_default="NONE", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="OPEN", nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("blocks IN ('NONE','APPROVAL','ISSUE')", name="ck_review_issues_blocks"),
        sa.CheckConstraint("severity IN ('error','warning','info')", name="ck_review_issues_severity"),
        sa.CheckConstraint("status <> 'WAIVED' OR char_length(btrim(coalesce(resolution_note, ''))) > 0", name="ck_review_issues_waiver_needs_reason"),
        sa.CheckConstraint("status = 'OPEN' OR resolved_at IS NOT NULL", name="ck_review_issues_resolved_at"),
        sa.CheckConstraint("status IN ('OPEN','RESOLVED','WAIVED')", name="ck_review_issues_status"),
        sa.CheckConstraint(
            "(CASE WHEN drawing_element_id IS NULL THEN 0 ELSE 1 END) "
            "+ (CASE WHEN ledger_id IS NULL THEN 0 ELSE 1 END) "
            "+ (CASE WHEN boq_item_id IS NULL THEN 0 ELSE 1 END) "
            "+ (CASE WHEN adjustment_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="ck_review_issues_single_target",
        ),
        sa.ForeignKeyConstraint(["adjustment_id", "organization_id"], ["boq_item_adjustments.id", "boq_item_adjustments.organization_id"], name="fk_review_issues_adjustment_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["boq_item_id", "organization_id"], ["boq_items.id", "boq_items.organization_id"], name="fk_review_issues_item_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"], name="fk_review_issues_version_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["calculation_run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"], name="fk_review_issues_run_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drawing_element_id"], ["drawing_elements.id"], name="fk_review_issues_element_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ledger_id", "organization_id"], ["quantity_ledger.id", "quantity_ledger.organization_id"], name="fk_review_issues_ledger_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_review_issues_project_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], name="fk_review_issues_resolved_by", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_issues_org_project_status", "review_issues", ["organization_id", "project_id", "status"], unique=False)
    op.create_index("ix_review_issues_version_status", "review_issues", ["boq_version_id", "status"], unique=False)
    op.create_index(
        "ix_review_issues_open_blocking", "review_issues", ["boq_version_id"],
        unique=False, postgresql_where=sa.text("status = 'OPEN' AND blocks <> 'NONE'"),
    )
    op.create_index(
        "uq_review_issues_version_dedupe", "review_issues", ["boq_version_id", "dedupe_key"],
        unique=True, postgresql_where=sa.text("boq_version_id IS NOT NULL"),
    )
    op.create_index(
        "uq_review_issues_project_dedupe", "review_issues", ["project_id", "dedupe_key"],
        unique=True, postgresql_where=sa.text("boq_version_id IS NULL"),
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("boq_version_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="QUEUED", nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=True),
        sa.Column("storage_key", sa.String(length=1000), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(length=60), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("format IN ('PDF','XLSX')", name="ck_export_jobs_format"),
        sa.CheckConstraint("kind IN ('CONTRACT_BOQ','PROCUREMENT','MEASUREMENT_BOOK','AUDIT_REPORT','REVISION_COMPARISON','BBS')", name="ck_export_jobs_kind"),
        sa.CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED')", name="ck_export_jobs_status"),
        sa.ForeignKeyConstraint(["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"], name="fk_export_jobs_version_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], name="fk_export_jobs_requested_by", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_id", "organization_id"], ["boq_snapshots.id", "boq_snapshots.organization_id"], name="fk_export_jobs_snapshot_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_org_version", "export_jobs", ["organization_id", "boq_version_id"], unique=False)
    op.create_index("ix_export_jobs_snapshot", "export_jobs", ["snapshot_id"], unique=False)

    op.create_foreign_key("fk_boq_versions_approved_by", "boq_versions", "users", ["approved_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_boq_versions_issued_by", "boq_versions", "users", ["issued_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_boq_versions_snapshot_id", "boq_versions", "boq_snapshots", ["snapshot_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_boq_versions_calculation_run_tenant", "boq_versions", "calculation_runs", ["calculation_run_id", "organization_id"], ["id", "organization_id"])
    op.create_index("ix_boq_versions_project_lifecycle", "boq_versions", ["project_id", "lifecycle"], unique=False)

    op.create_foreign_key("fk_boq_items_level_id", "boq_items", "building_levels", ["level_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_boq_items_calculation_run_tenant", "boq_items", "calculation_runs", ["calculation_run_id", "organization_id"], ["id", "organization_id"])
    op.create_index("ix_boq_items_org_version_work_item", "boq_items", ["organization_id", "boq_version_id", "work_item_code"], unique=False)
    op.create_index(
        "uq_boq_items_version_item_key", "boq_items", ["boq_version_id", "item_key"],
        unique=True, postgresql_where=sa.text("item_key IS NOT NULL"),
    )

    op.execute(
        """
        UPDATE boq_versions v SET
          lifecycle = CASE
            WHEN v.status::text = 'SUPERSEDED' THEN 'SUPERSEDED'
            WHEN EXISTS (SELECT 1 FROM boq_items i WHERE i.boq_version_id = v.id)
             AND NOT EXISTS (SELECT 1 FROM boq_items i
                             WHERE i.boq_version_id = v.id AND i.status::text <> 'APPROVED')
            THEN 'APPROVED'
            ELSE 'DRAFT' END,
          origin = CASE WHEN v.drawing_id IS NULL THEN 'MANUAL' ELSE 'LEGACY' END
        """
    )
    op.execute("UPDATE boq_items SET net_quantity = quantity WHERE net_quantity IS NULL")
    op.execute(
        """
        UPDATE boq_items SET source_kind = 'MANUAL', is_manual = true
        WHERE item_type::text = 'CUSTOM' AND drawing_element_id IS NULL
        """
    )

    op.create_check_constraint(
        "ck_boq_versions_lifecycle", "boq_versions",
        "lifecycle IN ('DRAFT','CALCULATING','CALCULATED','UNDER_REVIEW','APPROVED','ISSUED','SUPERSEDED','ARCHIVED')",
    )
    op.create_check_constraint("ck_boq_versions_origin", "boq_versions", "origin IN ('LEGACY','MANUAL','ENGINE')")
    op.create_check_constraint(
        "ck_boq_versions_issued_has_snapshot", "boq_versions",
        "lifecycle <> 'ISSUED' OR snapshot_id IS NOT NULL",
    )
    op.create_index(
        "uq_boq_versions_project_approved_engine", "boq_versions", ["project_id"],
        unique=True, postgresql_where=sa.text("origin = 'ENGINE' AND lifecycle IN ('APPROVED','ISSUED')"),
    )

    op.create_check_constraint(
        "ck_boq_items_source_kind", "boq_items",
        "source_kind IN ('LEGACY','MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE')",
    )
    op.create_check_constraint("ck_boq_items_review_status", "boq_items", "review_status IN ('OK','REVIEW_REQUIRED','WAIVED')")
    op.create_check_constraint(
        "ck_boq_items_canonical_unit", "boq_items",
        "canonical_unit IS NULL OR canonical_unit IN ('m3','m2','m','kg','nos')",
    )
    op.create_check_constraint("ck_boq_items_manual_consistent", "boq_items", "is_manual = (source_kind = 'MANUAL')")
    op.create_check_constraint("ck_boq_items_net_non_negative", "boq_items", "net_quantity IS NULL OR net_quantity >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_boq_items_net_non_negative", "boq_items", type_="check")
    op.drop_constraint("ck_boq_items_manual_consistent", "boq_items", type_="check")
    op.drop_constraint("ck_boq_items_canonical_unit", "boq_items", type_="check")
    op.drop_constraint("ck_boq_items_review_status", "boq_items", type_="check")
    op.drop_constraint("ck_boq_items_source_kind", "boq_items", type_="check")
    op.drop_index("uq_boq_versions_project_approved_engine", table_name="boq_versions")
    op.drop_constraint("ck_boq_versions_issued_has_snapshot", "boq_versions", type_="check")
    op.drop_constraint("ck_boq_versions_origin", "boq_versions", type_="check")
    op.drop_constraint("ck_boq_versions_lifecycle", "boq_versions", type_="check")

    op.drop_index("uq_boq_items_version_item_key", table_name="boq_items")
    op.drop_index("ix_boq_items_org_version_work_item", table_name="boq_items")
    op.drop_constraint("fk_boq_items_calculation_run_tenant", "boq_items", type_="foreignkey")
    op.drop_constraint("fk_boq_items_level_id", "boq_items", type_="foreignkey")
    op.drop_index("ix_boq_versions_project_lifecycle", table_name="boq_versions")
    op.drop_constraint("fk_boq_versions_calculation_run_tenant", "boq_versions", type_="foreignkey")
    op.drop_constraint("fk_boq_versions_snapshot_id", "boq_versions", type_="foreignkey")
    op.drop_constraint("fk_boq_versions_issued_by", "boq_versions", type_="foreignkey")
    op.drop_constraint("fk_boq_versions_approved_by", "boq_versions", type_="foreignkey")
    
    op.drop_table("export_jobs")
    op.drop_table("review_issues")
    op.drop_table("boq_item_ledger_links")
    op.drop_table("boq_snapshot_items")
    op.drop_table("boq_item_adjustments")
    op.drop_table("boq_snapshots")

    for column in (
        "engine_version", "calculation_run_id", "is_manual", "source_kind", "review_status",
        "adjustment_total", "unit_factor", "canonical_unit", "material_grade", "level_id", "item_key",
    ):
        op.drop_column("boq_items", column)
    for column in (
        "issued_at", "issued_by_user_id", "approved_at", "approved_by_user_id",
        "snapshot_id", "calculation_run_id", "origin", "lifecycle",
    ):
        op.drop_column("boq_versions", column)

    op.drop_constraint("uq_boq_items_id_org", "boq_items", type_="unique")
    op.drop_constraint("uq_boq_versions_id_org", "boq_versions", type_="unique")