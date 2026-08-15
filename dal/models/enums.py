import enum

# ========== 全大写的枚举 ==========
class CourseType(str, enum.Enum):
    """课程类型 - 全大写，匹配数据库"""
    REGULAR = "REGULAR"
    TRIAL = "TRIAL"
    SUMMER = "SUMMER"
    
    @property
    def label(self) -> str:
        """中文标签"""
        return {
            "REGULAR": "正课",
            "TRIAL": "体验课",
            "SUMMER": "暑假课"
        }[self.value]

class UserType(str, enum.Enum):
    """用户类型 - 全大写，匹配数据库"""
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"
    PARENT = "PARENT"
    
    @property
    def label(self) -> str:
        """中文标签"""
        return {
            "STUDENT": "学生",
            "TEACHER": "老师",
            "ADMIN": "管理员",
            "PARENT": "家长"
        }[self.value]

# ========== 全大写的枚举（name == value，匹配数据库） ==========
class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    CARD = "CARD"
    VOICE = "VOICE"
    FILE = "FILE"

class SenderType(str, enum.Enum):
    """发送者类型"""
    USER = "USER"
    ROBOT = "ROBOT"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"

class SessionType(str, enum.Enum):
    """会话类型"""
    AI_SERVICE = "AI_SERVICE"
    HUMAN_SERVICE = "HUMAN_SERVICE"
    TRANSFER = "TRANSFER"

class StudentCourseStatus(str, enum.Enum):
    """学生选课状态 - 全小写"""
    ACTIVE = "active"      # 已选/生效
    DROPPED = "dropped"    # 已退课
    COMPLETED = "completed"# 已完成

class PreScheduleStatus(str, enum.Enum):
    """预排课状态"""
    PENDING = "pending"  # 待审核
    APPROVED = "approved"  # 审核通过
    REJECTED = "rejected" # 审核拒绝

# ========== 数字枚举（非PostgreSQL枚举） ==========
class UserStatus(int, enum.Enum):
    """用户状态 - 数字类型"""
    ENABLE = 1
    DISABLE = 0

class CourseStatus(int, enum.Enum):
    """课程状态 - 数字类型"""
    ONLINE = 1 
    OFFLINE = 0 #

class ScheduleActiveStatus(int, enum.Enum):
    """正式排课状态"""
    ACTIVE = 1     # 生效中
    INACTIVE = 0   # 停用
class ScheduleStatus(int, enum.Enum):
    """排课审核状态 - 数字类型"""
    PENDING = 1   # 待审核
    APPROVED = 2  # 审核通过
    REJECTED = 3  # 审核拒绝
class ParentRelation(str, enum.Enum):
    """家长-学生关系"""
    FATHER = "father" # 父亲
    MOTHER = "mother" # 母亲
    GUARDIAN = "guardian" #监护人

# ========== 消课相关枚举 ==========
class TodoStatus(str, enum.Enum):
    """教师待办状态"""
    PENDING = "pending"        # 待处理：上课时间到，待消课待办已生成，等待教师确认
    DONE = "done"              # 已完成：教师已确认消课，课时已扣减
    CANCELLED = "cancelled"    # 已取消：排课取消/学生请假等情况下该待发作废

class NotificationType(str, enum.Enum):
    """通知类型 —— 覆盖课前一天 → 课前1小时 → 上课 → 课后消课 → 消课完成 全流程"""
    CLASS_REMINDER_DAY_BEFORE = "class_reminder_day_before"    # 前一天提醒：明天有课，推给学生+家长
    CLASS_REMINDER_HOUR_BEFORE = "class_reminder_hour_before"  # 课前1小时提醒：推给学生+家长
    CLASS_REMINDER = "class_reminder"              # 上课通知：上课时间到，推给老师和学生
    CONSUMPTION_PENDING = "consumption_pending"    # 待消课提醒：下课后推给老师
    CONSUMPTION_COMPLETED = "consumption_completed" # 消课完成通知：推给家长和老师

class ConsumptionStatus(str, enum.Enum):
    """消课状态 —— 记录每笔消课记录是确认还是取消"""
    CONFIRMED = "confirmed"    # 已确认：课时已消耗，学生剩余课时已扣减
    CANCELLED = "cancelled"    # 已取消：消课记录被撤销（误操作回滚/退课等场景）

# ========== 查询意图（业务逻辑用，非数据库） ==========
class QueryIntent(str, enum.Enum):
    """查询意图 - LangGraph用，全小写"""
    QUERY_USER_INFO = "query_user_info"
    QUERY_MY_COURSE = "query_my_course"
    QUERY_COURSE_DETAIL = "query_course_detail"
    QUERY_TEACHER_INFO = "query_teacher_info"
    COMPLAINT = "complaint"
    CONSULT = "consult"