# circuit/breaker.py
class CircuitBreaker:
    """
    第一阶段：空壳熔断
    只留类名，不写任何状态机、降级、滑动窗口！
    """
    def __init__(self):
        pass  # 空实现

    def is_available(self):
        return True  # 永远返回可用，占位用