import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE measurement_rule_sets DISABLE TRIGGER "trg_ruleset_immutable"'))
        print("Trigger DISABLED – now run the seed")

asyncio.run(main())
