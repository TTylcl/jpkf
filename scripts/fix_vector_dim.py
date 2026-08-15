import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
sys.stdout.reconfigure(encoding='utf-8')
from core.database import AsyncDatabase
from core import settings
from sqlalchemy import text

async def main():
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    async with AsyncDatabase.get_session() as session:
        result = await session.execute(text(
            "SELECT column_name, data_type, udt_name FROM information_schema.columns "
            "WHERE table_name = 'knowledge_chunks' AND column_name = 'embedding'"
        ))
        row = result.fetchone()
        print(f"Current column: {row}")

        await session.execute(text(
            "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector"
        ))
        await session.commit()
        print("Changed to unbounded vector type")

asyncio.run(main())
