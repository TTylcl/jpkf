# core/database.py - 纯异步版本
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import threading

class AsyncDatabase:
    """纯异步数据库管理器 - FastAPI最佳实践"""
    
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker] = None
    _lock = threading.Lock()
    
    @classmethod
    def init(
        cls, 
        database_url: str,
        echo: bool = False,
        pool_size: int = 20,
        max_overflow: int = 10
    ):
        """初始化数据库（程序启动时调用一次）"""
        with cls._lock:
            if cls._engine is not None:
                return
            
            cls._engine = create_async_engine(
                database_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,  # ✅ 连接健康检查
                pool_recycle=3600,   # ✅ 1小时回收连接
            )
            
            cls._session_factory = async_sessionmaker(
                cls._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
    
    @classmethod
    @asynccontextmanager
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话（依赖注入用）"""
        if cls._session_factory is None:
            raise RuntimeError("数据库未初始化，请先调用AsyncDatabase.init()")
        
        session = cls._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    @classmethod
    async def close(cls):
        """关闭数据库连接（程序退出时调用）"""
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None

# 使用示例
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖注入用"""
    async with AsyncDatabase.get_session() as session:
        yield session