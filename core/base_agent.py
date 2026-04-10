
#core/base_agent.py
from abc import ABC,abstractmethod
import uuid
from typing import List,Callable,Any
import settings
from core.context import AgentContext   
from core.registry import AgentRegistry 
from plugin.base_plugin import BasePlugin

#高级空壳
from circuit.breaker import CircuitBreaker
from topology.base_topology import BaseTopology
from exception.exc_manager import ExceptionManager

class BaseAgent(ABC):
    """
        基础代理类
        串联上下文、流水线、插件、生命周期，统一任务入口
        所有业务智能体必须继承此类并实现 process 方法
    """
    def __init__(self,context:AgentContext,registry:AgentRegistry):
        # 全局唯一注册表
        self.registry = registry
        # 智能体名称（从上下文获取，和你定义的规则一致）
        self.agent_name = self.__class__.__name__
        # 全局共享上下文（你的 loguru + 数据载体）
        self.context = context

        # 高级能力组件（完全按你的顺序编写）
        self.circuit_breaker = CircuitBreaker(self.agent_name)  # 熔断器
        self.topology = BaseTopology(self.agent_name)           # 拓扑调度
        self.exception_manager = ExceptionManager()             # 异常管理器

        # 生命周期状态
        self.is_running = False
        self.is_destroyed = False

        # 插件列表
        self.plugins: dict[str, BasePlugin] = {}
  
        # 初始化核心流水线
        self.pipeline: List[Callable[[Any], Any]] = []
    
    
    
    #智能体生命周期(启动、停止、销毁)  
    def start(self)->None:
        pass

    def stop(self)->None:
        pass
    def destroy(self)->None:
        pass

    #外部接口运行入口
    def run(self,*args,**kwargs)->Any:
        """外部接口运行入口"""
        self.start()
        self.process(*args,**kwargs)
        self.stop()
        self.destroy()

    


    @abstractmethod
    def process(self,*args,**kwargs)->Any:
        """核心处理逻辑"""
        pass

    #日志接口
    def log(self,level:str,message:str,module:str="BaseAgent",**kwargs)->None:
        """日志接口"""
        
        self.context.add_loglog(level,message,module,**kwargs)