# circuit/breaker.py
import pybreaker
from functools import wraps
from utils.logger import add_log
from core import settings

# --------------------------
# 全局统一管理所有熔断器实例，每个下游依赖对应独立熔断器，阈值可配置
# --------------------------
# 大模型接口专用熔断器：阈值从配置读，不用硬编码

llm_breaker = pybreaker.CircuitBreaker(
    fail_max=settings.CIRCUIT_FAILURE_THRESHOLD,# 阈值
    reset_timeout=settings.CIRCUIT_RECOVERY_TIME,# 熔断器重置时间
    name="llm_breaker",
    )
# 查课接口专用熔断器（示例，所有下游依赖都可以在这里新增独立熔断器）
course_api_breaker = pybreaker.CircuitBreaker(
    fail_max=settings.CIRCUIT_FAILURE_THRESHOLD,#
    reset_timeout=settings.CIRCUIT_RECOVERY_TIME,
    name="course_api_circuit_breaker"
)

# --------------------------
# 通用熔断装饰器：无侵入绑定到任意需要熔断的函数
# --------------------------
def with_circuit_breaker(breaker: pybreaker.CircuitBreaker,fallback_func):
    """
    通用熔断装饰器
    :param breaker: 对应下游依赖的熔断器实例
    :param fallback_func: 熔断触发后的业务降级函数，入参和原函数完全一致
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            #拿到ctx
            ctx = kwargs.get("ctx")
            if ctx is None:
                # 类方法第一个参数是self，从第二个参数开始找，跳过self避免误判
                for arg in args[1:]:
                    if hasattr(arg, "logs"):
                        ctx = arg
                        break
            try:
                return breaker.call(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError as e:
                # 熔断触发，执行降级逻辑
                add_log("ERROR", "熔断触发，执行降级逻辑：{}".format(e))
                return fallback_func(*args, **kwargs)
        return wrapper
    return decorator
