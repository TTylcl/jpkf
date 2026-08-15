# dal/models/__init__.py
"""
模型导入顺序控制
先导入 User，再导入 Course，避免循环导入问题
"""

# 1. 先导入 User
from dal.models.user_model import User

# 2. 再导入 Course
from dal.models.course_model import Course

# 其他模型...
from dal.models.schedule_model import Schedule
from dal.models.parent_student_model import ParentStudent
from dal.models.session_info_model import SessionInfo
from dal.models.chat_message_model import ChatMessage
# 消课模块新增模型
from dal.models.lesson_consumption_model import LessonConsumption
from dal.models.teacher_todo_model import TeacherTodo
from dal.models.notification_model import Notification
from dal.models.student_schedule_model import StudentSchedule
