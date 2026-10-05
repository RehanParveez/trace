import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE finish_rules DROP CONSTRAINT IF EXISTS ck_finish_rules_surface"))
        await conn.execute(text("""
            ALTER TABLE finish_rules
            ADD CONSTRAINT ck_finish_rules_surface
            CHECK (surface IN ('FLOOR', 'WALL', 'CEILING', 'SKIRTING', 'DADO', 'STAIR', 'WATERPROOFING'))
        """))
        print("Constraint updated successfully")

asyncio.run(main())
