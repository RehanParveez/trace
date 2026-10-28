from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d6f8a0c2e4b1"
down_revision = "a3c5e7f9b1d2"
branch_labels = None
depends_on = None

def upgrade() -> None:
  op.create_table(
    "rule_book",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    sa.Column("name", sa.String(80), nullable=False),
    sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("organization_id", "name", "version", name="uq_rule_book_org_name_version"),
  )
  
  op.create_index("ix_rule_book_org", "rule_book", ["organization_id"])
  op.create_index("uq_rule_book_active", "rule_book", ["organization_id"], unique=True, postgresql_where=sa.text("is_active"))
  op.create_table(
    "rule",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rule_book.id", ondelete="CASCADE"), nullable=False),
    sa.Column("key", sa.String(64), nullable=False),
    sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("unit", sa.String(24), nullable=True),
    sa.Column("cls", sa.String(12), nullable=False, server_default="JUDGEMENT"),
    sa.Column("origin", sa.String(24), nullable=False),
    sa.Column("note", sa.Text(), nullable=True),
    sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rule.id", ondelete="SET NULL", name="fk_rule_supersedes"), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("book_id", "key", "scope", name="uq_rule_book_key_scope"),
    sa.CheckConstraint("cls IN ('PRINTED','STANDARD','JUDGEMENT')", name="ck_rule_cls"),
    sa.CheckConstraint("origin IN ('COMPANY','QS_WORKBOOK','PROJECT','CODE_DEFAULT_ASSUMED')", name="ck_rule_origin"),
  )
  
  op.create_index("ix_rule_book", "rule", ["book_id"])
  op.create_table(
    "project_rule_override",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("key", sa.String(64), nullable=False),
    sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column("unit", sa.String(24), nullable=True),
    sa.Column("note", sa.Text(), nullable=True),
    sa.Column("set_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_project_rule_override_set_by"), nullable=True),
    sa.Column("set_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("project_id", "key", "scope", name="uq_project_rule_override_key_scope"),
  )
  
  op.create_index("ix_project_rule_override_project", "project_rule_override", ["project_id"])
  op.execute("""
    INSERT INTO rule_book (id, organization_id, name, version, is_active, created_at)
    SELECT gen_random_uuid(), organization_id, 'Company rules', 1, true, now()
    FROM company_conventions
    GROUP BY organization_id
  """)
  op.execute("""
    INSERT INTO rule (id, book_id, key, scope, value, unit, cls, origin, note, version, supersedes_id, created_at)
    SELECT gen_random_uuid(), b.id, c.key, '{}'::jsonb, c.value, c.unit, 'JUDGEMENT', c.origin, c.evidence, 1, NULL, now()
    FROM company_conventions c
    JOIN rule_book b ON b.organization_id = c.organization_id AND b.name = 'Company rules' AND b.version = 1
  """)

def downgrade() -> None:
  op.drop_index("ix_project_rule_override_project", table_name="project_rule_override")
  op.drop_table("project_rule_override")
  op.drop_index("ix_rule_book", table_name="rule")
  op.drop_table("rule")
  op.drop_index("uq_rule_book_active", table_name="rule_book")
  op.drop_index("ix_rule_book_org", table_name="rule_book")
  op.drop_table("rule_book")
