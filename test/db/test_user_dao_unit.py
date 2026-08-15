# scripts/test_db_connection.py
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def test_connection():
    """测试数据库连接"""
    from core import settings
    from core.database import AsyncDatabase
    
    print("🔍 开始测试数据库连接...")
    
    try:
        # 1. 初始化数据库
        print("1. 初始化数据库...")
        AsyncDatabase.init(settings.DB_URI_TEST,)
        print("   ✅ 数据库初始化成功")
        
        # 2. 测试连接
        print("2. 测试连接...")
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with AsyncDatabase.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            data = result.scalar()
            print(f"   ✅ 连接测试成功: SELECT 1 = {data}")
            
        # 3. 测试事务
        print("3. 测试事务...")
        async with AsyncDatabase.get_session() as session:
            # 创建测试表（如果不存在）
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS connection_test (
                    id SERIAL PRIMARY KEY,
                    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 插入测试数据
            await session.execute(
                text("INSERT INTO connection_test DEFAULT VALUES")
            )
            
            # 查询测试数据
            result = await session.execute(
                text("SELECT COUNT(*) FROM connection_test")
            )
            count = result.scalar()
            print(f"   ✅ 事务测试成功: 表中有 {count} 条记录")
            
        print("🎉 所有数据库测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())