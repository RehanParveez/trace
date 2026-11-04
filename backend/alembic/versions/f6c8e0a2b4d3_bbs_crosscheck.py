"""bbs cross-check: CHECK finding class, weight-effect basis and convention on findings

Revision ID: f6c8e0a2b4d3
Revises: e5b7d9f1a3c2
Create Date: 2026-11-04 17:48:00.000000
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f6c8e0a2b4d3'
down_revision: Union[str, Sequence[str], None] = 'e5b7d9f1a3c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD = "'ERROR','METHOD','ROUNDING','CONFLICT','MISSING','EXTRA','UNVERIFIABLE','NAMING','INFO'"
NEW = "'ERROR','METHOD','ROUNDING','CONFLICT','MISSING','EXTRA','UNVERIFIABLE','NAMING','CHECK','INFO'"

def upgrade() -> None:
    op.add_column("rebar_audit_findings", sa.Column("effect_basis", sa.String(12), nullable=True))
    op.add_column("rebar_audit_findings", sa.Column("convention", postgresql.JSONB(), nullable=True))
    op.drop_constraint("ck_rebar_audit_findings_class", "rebar_audit_findings", type_="check")
    op.create_check_constraint("ck_rebar_audit_findings_class", "rebar_audit_findings", f"finding_class IN ({NEW})")

def downgrade() -> None:
    op.execute("DELETE FROM rebar_audit_findings WHERE finding_class = 'CHECK'")
    op.drop_constraint("ck_rebar_audit_findings_class", "rebar_audit_findings", type_="check")
    op.create_check_constraint("ck_rebar_audit_findings_class", "rebar_audit_findings", f"finding_class IN ({OLD})")
    op.drop_column("rebar_audit_findings", "convention")
    op.drop_column("rebar_audit_findings", "effect_basis")
