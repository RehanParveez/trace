"""row level security by scope: tenant, system, dispatch and granted support (replaces the blanket platform-admin bypass on tenant tables)

Revision ID: 8f5b2d0c3e21
Revises: 7e4a1c9b2d10
Create Date: 2026-10-19 02:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8f5b2d0c3e21'
down_revision: Union[str, Sequence[str], None] = '7e4a1c9b2d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "trace_runtime"

IDENTITY_TABLES = {
    "users", "roles", "organization_memberships", "refresh_tokens", "organization_invitations",
    "organizations", "permissions", "role_permissions", "plans", "platform_admins",
}

CONTROL_PLANE_TABLES = {"subscriptions", "usage_counters"}
DISPATCH_TABLES = {
    "drawings", "calculation_runs", "run_stage_log", "export_jobs",
    "staged_quantity_solids", "staged_quantity_ledger", "staged_ledger_deductions", "staged_rebar_bar_marks",
    "whatsapp_channels", "whatsapp_messages", "data_export_jobs", "organization_deletion_requests",
}

CHILD_TABLES = {
    "assembly_recipe_components": ("recipe_id", "assembly_recipes"),
    "element_type_mappings": ("rule_set_id", "measurement_rule_sets"),
    "finish_rules": ("rule_set_id", "measurement_rule_sets"),
    "material_wastage_rules": ("rule_set_id", "measurement_rule_sets"),
    "opening_measurement_rules": ("rule_set_id", "measurement_rule_sets"),
    "reinforcement_rules": ("rule_set_id", "measurement_rule_sets"),
    "milestones": ("project_id", "projects"),
    "project_members": ("project_id", "projects"),
}
SUPPORT_CAN_APPEND = {"audit_log"}
NO_SUPPORT_READ = {"organization_keys"}
NO_FORCE = {"support_access_grants"}

ORG = "NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"
DISPATCH = "current_setting('app.service_scope', true) = 'dispatch'"
SYSTEM = "current_setting('app.system_maintenance', true) = 'true'"
SUPPORT_ORG = "NULLIF(current_setting('app.support_org_id', true), '')::uuid"

def tenant(col: str) -> str:
    return f"{col} = {ORG}"

def support(col: str) -> str:
    return f"({ADMIN} AND {col} = {SUPPORT_ORG} AND support_grant_active({col}))"

def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def _drop_policies(conn, table: str) -> None:
    names = conn.execute(sa.text("SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = :t"), {"t": table}).scalars().all()
    for name in names:
        op.execute(f"DROP POLICY IF EXISTS {_q(name)} ON {_q(table)}")

def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {_q(table)} ENABLE ROW LEVEL SECURITY")
    if table in NO_FORCE:
        op.execute(f"ALTER TABLE {_q(table)} NO FORCE ROW LEVEL SECURITY")
    else:
        op.execute(f"ALTER TABLE {_q(table)} FORCE ROW LEVEL SECURITY")

def policy_statements(table: str, kind: str, nullable: bool = False, parent: tuple[str, str] | None = None) -> list[str]:
    """The CREATE POLICY statements for one table. kind: 'plain', 'control', 'child'. Pure, so tests can inspect it."""
    t = _q(table)
    out: list[str] = []
    if kind == "control":
        out.append(f"CREATE POLICY {_q(table + '_org_isolation')} ON {t} FOR ALL USING ({tenant('organization_id')} OR {ADMIN}) WITH CHECK ({tenant('organization_id')} OR {ADMIN})")
        return out
    if kind == "child":
        fk, parent_table = parent
        p = _q(parent_table)
        read = f"EXISTS (SELECT 1 FROM {p} p WHERE p.id = {t}.{_q(fk)})"
        write = (f"EXISTS (SELECT 1 FROM {p} p WHERE p.id = {t}.{_q(fk)} AND "
                 f"(p.organization_id = {ORG} OR (p.organization_id IS NULL AND {SYSTEM})))")
        out.append(f"CREATE POLICY {_q(table + '_read')} ON {t} FOR SELECT USING ({read})")
        out.append(f"CREATE POLICY {_q(table + '_ins')} ON {t} FOR INSERT WITH CHECK ({write})")
        out.append(f"CREATE POLICY {_q(table + '_upd')} ON {t} FOR UPDATE USING ({write}) WITH CHECK ({write})")
        out.append(f"CREATE POLICY {_q(table + '_del')} ON {t} FOR DELETE USING ({write})")
        return out
    if nullable:
        read = f"organization_id IS NULL OR {tenant('organization_id')} OR {support('organization_id')}"
        write = f"{tenant('organization_id')} OR (organization_id IS NULL AND {SYSTEM})"
        out.append(f"CREATE POLICY {_q(table + '_read')} ON {t} FOR SELECT USING ({read})")
        out.append(f"CREATE POLICY {_q(table + '_ins')} ON {t} FOR INSERT WITH CHECK ({write})")
        out.append(f"CREATE POLICY {_q(table + '_upd')} ON {t} FOR UPDATE USING ({write}) WITH CHECK ({write})")
        out.append(f"CREATE POLICY {_q(table + '_del')} ON {t} FOR DELETE USING ({write})")
    else:
        out.append(f"CREATE POLICY {_q(table + '_org_isolation')} ON {t} FOR ALL USING ({tenant('organization_id')}) WITH CHECK ({tenant('organization_id')})")
        if table not in NO_SUPPORT_READ:
            out.append(f"CREATE POLICY {_q(table + '_support_read')} ON {t} FOR SELECT USING ({support('organization_id')})")
    if table in SUPPORT_CAN_APPEND:
        out.append(f"CREATE POLICY {_q(table + '_support_append')} ON {t} FOR INSERT WITH CHECK ({support('organization_id')})")
    if table in DISPATCH_TABLES:
        out.append(f"CREATE POLICY {_q(table + '_dispatch')} ON {t} FOR ALL USING ({DISPATCH}) WITH CHECK ({DISPATCH})")
    return out

def _org_tables(conn) -> list[tuple[str, bool]]:
    rows = conn.execute(sa.text("""
        SELECT c.table_name, (c.is_nullable = 'YES') AS nullable
        FROM information_schema.columns c
        JOIN information_schema.tables t ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = 'public' AND c.column_name = 'organization_id' AND c.data_type = 'uuid'
          AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_name
    """)).all()
    return [(name, bool(nullable)) for name, nullable in rows if name not in IDENTITY_TABLES]

def _existing(conn, names) -> set[str]:
    rows = conn.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")).scalars().all()
    return set(rows) & set(names)

def upgrade() -> None:
    conn = op.get_bind()

    op.execute("""
        CREATE OR REPLACE FUNCTION support_grant_active(org uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
          SELECT EXISTS (
            SELECT 1 FROM support_access_grants g
            WHERE g.organization_id = org AND g.revoked_at IS NULL AND g.starts_at <= now() AND g.expires_at > now()
          )
        $$
    """)

    done: list[str] = []
    for table, nullable in _org_tables(conn):
        kind = "control" if table in CONTROL_PLANE_TABLES else "plain"
        _drop_policies(conn, table)
        _enable(table)
        for stmt in policy_statements(table, kind, nullable=nullable and kind == "plain"):
            op.execute(stmt)
        done.append(table)

    present = _existing(conn, set(CHILD_TABLES) | {p for _, p in CHILD_TABLES.values()})
    for child, (fk, parent) in CHILD_TABLES.items():
        if child not in present or parent not in present:
            continue
        _drop_policies(conn, child)
        _enable(child)
        for stmt in policy_statements(child, "child", parent=(fk, parent)):
            op.execute(stmt)

    has_role = conn.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": RUNTIME_ROLE}).scalar()
    if has_role:
        op.execute(f"GRANT USAGE ON SCHEMA public TO {RUNTIME_ROLE}")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {RUNTIME_ROLE}")
        op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RUNTIME_ROLE}")
        op.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {RUNTIME_ROLE}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {RUNTIME_ROLE}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {RUNTIME_ROLE}")

def downgrade() -> None:
    """Back to one policy per table that lets a platform admin through (the position before this migration). The grants stay."""
    conn = op.get_bind()
    for table, nullable in _org_tables(conn):
        _drop_policies(conn, table)
        _enable(table)
        cond = f"({'organization_id IS NULL OR ' if nullable else ''}{tenant('organization_id')} OR {ADMIN})"
        op.execute(f"CREATE POLICY {_q(table + '_org_isolation')} ON {_q(table)} FOR ALL USING {cond} WITH CHECK {cond}")
    present = _existing(conn, set(CHILD_TABLES))
    for child in CHILD_TABLES:
        if child in present:
            _drop_policies(conn, child)
            op.execute(f"ALTER TABLE {_q(child)} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS support_grant_active(uuid)")
