"""
Redis客户端 - 极简版
只保留核心功能，其他按需添加
"""
import json
import redis
from typing import Any, Optional

class RedisClient:
    """Redis客户端"""
    # 初始化
    def __init__(self, host: str, port: int, password: str = None, db: int = 0):
        self.client = redis.Redis(
            # 连接参数
            host=host, port=port, password=password, db=db,
            decode_responses=False,
            max_connections=10
        )
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存"""
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        return self.client.set(key, value, ex=expire)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        value = self.client.get(key) #
        if value is None:
            return None
        value = value.decode("utf-8") 
        try:
            return json.loads(value)
        except:
            return value
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        return self.client.delete(key) > 0
    
    def try_lock(self, key: str, expire: int = 10) -> bool:
        """尝试获取锁"""
        return self.client.set(key, "1", ex=expire, nx=True)
    
    def release_lock(self, key: str):
        """释放锁"""
        self.client.delete(key)


# 全局实例
redis_client = None

def init_redis(host: str, port: int, password: str = None, db: int = 0):
    """初始化Redis连接"""
    global redis_client
    redis_client = RedisClient(host, port, password, db)
    return redis_client

def get_redis() -> RedisClient:
    """获取Redis实例"""
    if redis_client is None:
        raise RuntimeError("Redis未初始化，请先调用 init_redis()")
    return redis_client