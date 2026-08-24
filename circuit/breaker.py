# circuit/breaker.py
"""熔断器 —— 保护下游依赖（LLM / RAG 等），连续失败自动降级

为什么不用 pybreaker：
- pybreaker 的 `call` 是同步的，`call_async` 依赖 tornado（本项目是 asyncio，未装 tornado），
  无法直接用在 async 代码里。所以这里实现一个轻量、async 原生的熔断器，
  状态机和 pybreaker 完全一致：closed → open → half_open → closed。

三态语义：
- closed（正常）：放行请求；连续失败达到 fail_max 则打开
- open（熔断）：直接快速失败，不再打下游；过了 reset_timeout 进入 half_open
- half_open（半开）：放行一个试探请求，成功→closed，失败→open
"""
import asyncio
import time
from functools import wraps

from utils.logger import add_log
from core import settings


class CircuitBreakerOpen(Exception):
    """熔断器处于打开状态时抛出，供调用方捕获并降级"""


class AsyncCircuitBreaker:
    """异步熔断器：连续失败达到阈值则打开，冷却后进入半开探测"""

    def __init__(self, name: str, fail_max: int, reset_timeout: int):
        self.name = name
        self.fail_max = fail_max              # 连续失败多少次后打开
        self.reset_timeout = reset_timeout    # 打开后冷却多久（秒）进入半开
        self._state = "closed"                # closed / open / half_open
        self._failure_count = 0
        self._opened_at = 0.0                 # 打开时刻（monotonic 秒）
        self._lock = asyncio.Lock()

    @property
    def current_state(self) -> str:
        return self._state

    async def call(self, func, *args, **kwargs):
        """按熔断器状态执行 func，返回结果

        步骤：
        1. open 且未冷却 → 抛 CircuitBreakerOpen（快速失败，不打下游）
        2. open 但已冷却 → 转 half_open，放行一个试探请求
        3. 真正调用 func；失败记一次、成功清零
        """
        # 步骤 1-2：状态判断（锁内，避免并发竞态）
        async with self._lock:
            if self._state == "open":
                if time.monotonic() - self._opened_at < self.reset_timeout:
                    raise CircuitBreakerOpen(f"熔断器[{self.name}]已打开，快速失败降级")
                self._state = "half_open"

        # 步骤 3：真正调用（锁外执行，不阻塞其他请求）
        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            await self._on_failure(e)
            raise
        await self._on_success()
        return result

    async def _on_failure(self, exc: Exception) -> None:
        """记录失败：计数 +1，达到阈值或半开期间失败则打开"""
        async with self._lock:
            self._failure_count += 1
            if self._state == "half_open" or self._failure_count >= self.fail_max:
                self._state = "open"
                self._opened_at = time.monotonic()
                add_log(
                    "ERROR",
                    f"熔断器[{self.name}]打开（连续失败 {self._failure_count} 次）",
                    module="circuit",
                )

    async def _on_success(self) -> None:
        """记录成功：清零失败计数，半开状态恢复为关闭"""
        async with self._lock:
            self._failure_count = 0
            if self._state == "half_open":
                self._state = "closed"
                add_log("INFO", f"熔断器[{self.name}]恢复 closed", module="circuit")


# ── 全局实例：每个下游依赖一个独立熔断器（阈值从配置读）──
llm_breaker = AsyncCircuitBreaker(
    name="llm_breaker",
    fail_max=settings.CIRCUIT_FAILURE_THRESHOLD,
    reset_timeout=settings.CIRCUIT_RECOVERY_TIME,
)
# 示例：其他下游依赖（如外部课程 API）可照此新增独立熔断器
course_api_breaker = AsyncCircuitBreaker(
    name="course_api_breaker",
    fail_max=settings.CIRCUIT_FAILURE_THRESHOLD,
    reset_timeout=settings.CIRCUIT_RECOVERY_TIME,
)


# ── 通用异步熔断装饰器：无侵入绑定到任意 async 函数 ──
def with_circuit_breaker(breaker: AsyncCircuitBreaker, fallback_func):
    """把任意 async 函数包上熔断保护

    :param breaker: 熔断器实例
    :param fallback_func: 熔断/失败时的降级函数，入参与原函数完全一致

    注意：无论「单次失败」还是「熔断打开」，都会降级到 fallback_func，
    避免把下游的内部错误直接暴露给用户；熔断器只负责「是否跳过调用 + 记账」。
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await breaker.call(func, *args, **kwargs)
            except Exception as e:
                add_log("ERROR", f"熔断器[{breaker.name}]降级: {e}", module="circuit")
                return fallback_func(*args, **kwargs)

        return wrapper

    return decorator
