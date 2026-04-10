# topology/base_topology.py
from abc import ABC

class BaseTopology(ABC):
    """
    第一阶段：空壳拓扑
    只留抽象类，不写调度！
    """
    def __init__(self, context):
        self.context = context