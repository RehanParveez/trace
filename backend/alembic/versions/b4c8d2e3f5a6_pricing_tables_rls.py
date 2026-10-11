from typing import Sequence, Union

from alembic import op

revision: str = 'b4c8d2e3f5a6'
down_revision: Union[str, Sequence[str], None] = 'a3b7c1d2e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
ADMIN = "current_setting('app.is_platform_admin', true) = 'true'"

TENANT_ONLY = ["project_rate_overrides"]
SYSTEM_ROW = ["rate_books", "rate_items", "rate_analyses", "rate_book_escalations", "rate_analysis_components"]

def _enable(table: str, using: str, check: str) -> None:
  op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
  op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
  op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
  op.execute(f"CREATE POLICY {table}_org_isolation ON {table} USING ({using}) WITH CHECK ({check})")

def upgrade() -> None:
  for t in TENANT_ONLY:
    _enable(t, f"{TENANT} OR {ADMIN}", f"{TENANT} OR {ADMIN}")
  for t in SYSTEM_ROW:
    _enable(t, f"organization_id IS NULL OR {TENANT} OR {ADMIN}", f"{TENANT} OR {ADMIN}")

def downgrade() -> None:
  for t in [*TENANT_ONLY, *SYSTEM_ROW]:
    op.execute(f"DROP POLICY IF EXISTS {t}_org_isolation ON {t}")
    op.execute(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")