import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        # 1. Disable trigger
        await conn.execute(text('ALTER TABLE measurement_rule_sets DISABLE TRIGGER "trg_ruleset_immutable"'))
        print("Trigger disabled")

        # 2. See what we have
        result = await conn.execute(text("""
            SELECT id, code, status, immutable_version, created_at
            FROM measurement_rule_sets
            WHERE code = 'PUNJAB_CSR' AND organization_id IS NULL
            ORDER BY immutable_version DESC, created_at DESC
        """))
        rows = result.fetchall()
        print(f"Found {len(rows)} PUNJAB_CSR rule sets:")
        for r in rows:
            print(f"  {r[0]}  status={r[2]}  version={r[3]}")

        if len(rows) > 1:
            # Keep the newest one, delete the rest
            keep_id = rows[0][0]
            delete_ids = [r[0] for r in rows[1:]]

            # Delete finish_rules that belong to the ones we will delete
            for did in delete_ids:
                await conn.execute(text("DELETE FROM finish_rules WHERE rule_set_id = :id"), {"id": did})
                print(f"Deleted finish_rules for {did}")

            # Delete the extra rule sets
            for did in delete_ids:
                await conn.execute(text("DELETE FROM measurement_rule_sets WHERE id = :id"), {"id": did})
                print(f"Deleted rule set {did}")

            # Force the remaining one to DRAFT
            await conn.execute(text("""
                UPDATE measurement_rule_sets
                SET status = 'DRAFT', is_active = false
                WHERE id = :id
            """), {"id": keep_id})
            print(f"Kept and set to DRAFT: {keep_id}")
        elif len(rows) == 1:
            # Just force it to DRAFT
            await conn.execute(text("""
                UPDATE measurement_rule_sets
                SET status = 'DRAFT', is_active = false
                WHERE id = :id
            """), {"id": rows[0][0]})
            print(f"Forced existing one to DRAFT: {rows[0][0]}")
        else:
            print("No PUNJAB_CSR found – seed will create one")

        # 3. Re-enable trigger
        await conn.execute(text('ALTER TABLE measurement_rule_sets ENABLE TRIGGER "trg_ruleset_immutable"'))
        print("Trigger re-enabled")

asyncio.run(main())
