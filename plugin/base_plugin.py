#plugin/base_plugin.py
from abc import ABC, abstractmethod  #
from core.context import AgentContext  #导入共享上下文（后续会写，先这么导入）
from core.registry import AgentRegistry #全局注册表



class BasePlugin(ABC):
    """
        插件基类

    """
    def __init__(self, context:AgentContext,registry:AgentRegistry):
        #插件初始化
        self.context = context
        #全局注册表
        self.registry = registry
        #插件名称
        self.plugin_name = self.__class__.__name__

    @abstractmethod
    def run(self)->None:
        """
        插件运行方法
        :return:
        """
        pass
    @abstractmethod
    def stop(self)->None:
        """
        插件停止方法
        :return:
        """
        pass