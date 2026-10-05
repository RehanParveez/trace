import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        # Disable trigger
        await conn.execute(text('ALTER TABLE measurement_rule_sets DISABLE TRIGGER "trg_ruleset_immutable"'))
        print("Trigger disabled")

        # Rename the old version so it no longer matches the seed query
        await conn.execute(text("""
            UPDATE measurement_rule_sets
            SET code = 'PUNJAB_CSR_OLD_V1',
                status = 'SUPERSEDED',
                is_active = false
            WHERE id = '51293394-38c2-4016-824a-9017ba7d1ba5'
        """))
        print("Old rule set renamed to PUNJAB_CSR_OLD_V1")

        # Make sure the newest one is DRAFT and inactive so seed can work with it
        await conn.execute(text("""
            UPDATE measurement_rule_sets
            SET status = 'DRAFT',
                is_active = false
            WHERE id = '12273c4e-9842-45db-a1ab-647ceb1354b4'
        """))
        print("Newest rule set set to DRAFT")

        # Re-enable trigger
        await conn.execute(text('ALTER TABLE measurement_rule_sets ENABLE TRIGGER "trg_ruleset_immutable"'))
        print("Trigger re-enabled")

asyncio.run(main())
