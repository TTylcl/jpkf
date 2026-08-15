from enum import Enum

class DataMode(Enum):
    DEMO = "demo"      # 面试演示：内存数据
    DB = "database"    # 完整展示：真实ORM

# 面试时设置为DEMO
CURRENT_MODE = DataMode.DEMO