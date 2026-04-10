
"""
系统核心配置
统一管理所有固定参数 阈值 开关 端口
常量 引用本模块
"""

# 1系统核心配置
SYSTEM_NAME =  "基于pipeline的情感学习系统"
PYPROJECT_PATH = "pyproject.toml"  # 项目依赖路径
BEBUG_MODE = True   # 调试模式
ENCODING = "utf-8"

#2通信配置
WS_HOST = "127.0.0.1"
WS_PORT = 8080
WS_CONNECTION_TIMEOUT = 10

#3熔断配置
#最大重试次数
CIRCUIT_MAX_RETRY = 3
# 熔断器失败阈值
CIRCUIT_FAILURE_THRESHOLD = 2
# 熔断器恢复时间
CIRCUIT_RECOVERY_TIME = 5
# 滑动窗口：只统计最近N次请求的失败率
CIRCUIT_WINDOW_SIZE = 10
# 熔断降级提示语
CIRCUIT_DEGRADE_MESSAGE = "服务繁忙，已触发熔断降级，请稍后重试"
# 连续失败次数
CONTINUOUS_FAIL_COUNT = 0

# 4日志配置
LOG_ENABLED = True
# 日志格式开关
LOG_SHOW_TIMESTAMP = True    # 显示时间戳
LOG_SHOW_AGENT_NAME = True   # 显示Agent名称
LOG_SHOW_PLUGIN_NAME = True  # 显示插件名称
LOG_DIR = "logs"
LOG_ROTATION = "1 day"
LOG_RETENTION = "90 days"


# 日志级别：INFO / PROGRESS / ERROR
LOG_DEFAULT_LEVEL = "DEBUG" # 默认日志级别
LOG_LEVEL = "INFO"
API_LEVEL = "info"
#5Pipeline 流水线默认配置
# 默认流水线步骤（固定三步）
DEFAULT_PIPELINE_STEPS = [
    "pre_process",
    "process",
    "post_process"
]
# 流水线执行超时（秒）
PIPELINE_EXECUTE_TIMEOUT = 20


# 【6】拓扑结构默认配置

# 默认拓扑类型：linear(线性) / dag(有向无环图)
DEFAULT_TOPOLOGY = "linear"

# 【7】插件系统默认配置

# 系统启动时自动挂载的插件
AUTO_MOUNT_PLUGINS = ["LogPlugin"]
# 插件注册名称（统一规范）
PLUGIN_NAME_LOG = "LogPlugin"
PLUGIN_NAME_MEMORY = "MemoryPlugin"

# 【8】Agent 基础配置
# ==============================================
AGENT_DEFAULT_NAME = "找我来聊天吧"
AGENT_TASK_INPUT_MAX_LENGTH = 1000  # 任务输入最大长度
ACTIVE_PROMPT = 'v1'  # 激活提示

#