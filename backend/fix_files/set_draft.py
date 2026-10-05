import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            UPDATE measurement_rule_sets
            SET status = 'DRAFT'
            WHERE id = '51293394-38c2-4016-824a-9017ba7d1ba5'
        """))
        print("Rule set set to DRAFT")

asyncio.run(main())
