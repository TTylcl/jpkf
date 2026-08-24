import sys, asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import text
from core.database import AsyncDatabase
from core import settings
from core.security import hash_password

DEFAULT_PASSWORD = "123456"   # 演示统一密码，生产环境务必删除

async def main():
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    async with AsyncDatabase.get_session() as session:
        # 1. 加列（幂等，重复跑不会报错）
        await session.execute(text(
            "ALTER TABLE user_info ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
        ))
        # 2. 回填：所有还没密码的用户（含管理员）统一设默认密码
        hashed = hash_password(DEFAULT_PASSWORD)
        await session.execute(text(
            "UPDATE user_info SET password_hash = :h WHERE password_hash IS NULL"
        ), {"h": hashed})
        await session.commit()
        print(f"✅ password_hash 列已添加，默认密码回填为 '{DEFAULT_PASSWORD}'")
    await AsyncDatabase.close()

if __name__ == "__main__":
    asyncio.run(main())