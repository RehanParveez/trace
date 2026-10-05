import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        # Disable the immutability trigger
        await conn.execute(text('ALTER TABLE measurement_rule_sets DISABLE TRIGGER "trg_ruleset_immutable"'))
        print("Trigger disabled")

asyncio.run(main())
