"""
core/scheduler.py
后台调度器 —— 每分钟检查排课，自动生成教师待办和通知

【设计说明】
✅ 使用 APScheduler AsyncIOScheduler，原生异步，不阻塞 FastAPI 事件循环
✅ 每分钟扫描一次，查找当前时间匹配的活跃排课
✅ 为每门课的在读学生生成教师待办（TeacherTodo）
✅ 同时发送三种通知：
   ① CLASS_REMINDER → 老师 + 学生（上课提醒）
   ② CONSUMPTION_PENDING → 老师（课后提醒确认消课）
✅ 防重复：同一天同一排课不会重复生成待办

【为什么不用 Service 层】
调度器没有 CTX（用户上下文），直接使用 DAO + AsyncDatabase.get_session()
"""

from __future__ import annotations
import asyncio
from datetime import datetime, date, time, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.database import AsyncDatabase
from dal.dao.schedule_dao import ScheduleDao
from dal.dao.student_schedule_dao import StudentScheduleDao
from dal.dao.student_course_dao import StudentCourseDao
from dal.dao.teacher_todo_dao import TeacherTodoDao
from dal.dao.notification_dao import NotificationDao
from dal.dao.course_dao import CourseDao
from dal.dao.parent_student_dao import ParentStudentDao
from dal.models.enums import (
    ScheduleActiveStatus, NotificationType, TodoStatus,
)
from utils.logger import add_log

# 全局调度器实例
scheduler: AsyncIOScheduler | None = None


async def _check_and_create_todos():
    """
    每分钟执行一次的核心任务：

    1. 查当前时间（精确到分钟）匹配的活跃排课
    2. 对每个排课，找到该课程的所有在读学生
    3. 为每个 (教师, 排课, 学生) 生成一条待办
    4. 发送通知给教师和学生
    """
    now = datetime.now()
    today = date.today()
    current_day = now.isoweekday()  # 1=Monday ... 7=Sunday
    current_minute = time(now.hour, now.minute)

    try:
        async with AsyncDatabase.get_session() as session:
            schedule_dao = ScheduleDao(session)

            # 查询当天所有活跃排课
            schedules = await schedule_dao.find_all(
                day_of_week=current_day,
                status=ScheduleActiveStatus.ACTIVE.value,
            )

            # 精确匹配 start_time == 当前分钟
            matching = [
                s for s in schedules
                if s.start_time.hour == current_minute.hour
                and s.start_time.minute == current_minute.minute
            ]

            if not matching:
                return  # 当前分钟没有排课，直接返回

            todo_dao = TeacherTodoDao(session)
            ss_dao = StudentScheduleDao(session)
            sc_dao = StudentCourseDao(session)
            notif_dao = NotificationDao(session)
            course_dao = CourseDao(session)

            # 预加载课程名映射
            course_names: dict[int, str] = {}
            for s in matching:
                if s.course_id not in course_names:
                    course = await course_dao.get_by_id(s.course_id)
                    course_names[s.course_id] = course.course_name if course else f"课程{s.course_id}"

            for schedule in matching:
                # 防重复：该排课今天的待办是否已生成
                already_exists = await todo_dao.todo_exists(schedule.id, today)
                if already_exists:
                    add_log("info", f"排课#{schedule.id} 今日待办已存在，跳过", module="Scheduler",
                            schedule_id=schedule.id)
                    continue

                # 找到分配到这节课的学生（不是课程的所有学生）
                assignments = await ss_dao.get_schedule_students(schedule.id)

                add_log("info",
                        f"排课#{schedule.id} 课程#{schedule.course_id} 教师#{schedule.teacher_id} "
                        f"分配到 {len(assignments)} 个学生",
                        module="Scheduler",
                        schedule_id=schedule.id, course_id=schedule.course_id,
                        teacher_id=schedule.teacher_id)

                student_count = 0
                for ass in assignments:
                    student_name = ass.student.real_name if ass.student else f"学生{ass.student_id}"

                    # 查该学生的报名状态和剩余课时
                    enrollment = await sc_dao.get_by_student_and_course(ass.student_id, schedule.course_id)
                    if not enrollment or enrollment.status != "active":
                        add_log("info",
                                f"{student_name} 未报名或已退课，跳过",
                                module="Scheduler", student_id=ass.student_id)
                        continue
                    if not enrollment.remaining_lessons or enrollment.remaining_lessons <= 0:
                        add_log("info",
                                f"{student_name} 剩余课时为0，跳过",
                                module="Scheduler", student_id=ass.student_id)
                        continue

                    # ① 创建教师待办
                    course_name = course_names.get(schedule.course_id, f"课程{schedule.course_id}")
                    todo = await todo_dao.create_todo(
                        teacher_id=schedule.teacher_id,
                        schedule_id=schedule.id,
                        course_id=schedule.course_id,
                        student_id=ass.student_id,
                        todo_date=today,
                        title=f"待消课：{student_name} - {course_name} {today} {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}",
                        detail=(
                            f"学生剩余 {enrollment.remaining_lessons} 课时，"
                            f"教室: {schedule.classroom or '未指定'}"
                        ),
                    )
                    student_count += 1
                    add_log("info",
                            f"✅ 待办已生成 id={todo.id}：教师#{schedule.teacher_id} → "
                            f"{student_name} 课程#{schedule.course_id}",
                            module="Scheduler", todo_id=todo.id,
                            teacher_id=schedule.teacher_id, student_id=ass.student_id)

                    # ② 通知学生：上课提醒
                    await notif_dao.create_notification(
                        recipient_id=ass.student_id,
                        recipient_role="STUDENT",
                        notification_type=NotificationType.CLASS_REMINDER.value,
                        title="上课提醒",
                        content=f"您有一节{course_name} 即将在 {schedule.start_time} 开始，"
                                f"教室: {schedule.classroom or '未指定'}，请准时参加。",
                        ref_id=schedule.id,
                        ref_type="schedule",
                    )

                # ③ 通知教师：上课提醒（一门课只发一次）
                await notif_dao.create_notification(
                    recipient_id=schedule.teacher_id,
                    recipient_role="TEACHER",
                    notification_type=NotificationType.CLASS_REMINDER.value,
                    title="上课提醒",
                    content=f"您有一节排课#{schedule.id}（课程{schedule.course_id}）"
                            f"将在 {schedule.start_time} 开始，"
                            f"教室: {schedule.classroom or '未指定'}，请准备上课。",
                    ref_id=schedule.id,
                    ref_type="schedule",
                )

                # ④ 通知教师：课后待消课提醒
                await notif_dao.create_notification(
                    recipient_id=schedule.teacher_id,
                    recipient_role="TEACHER",
                    notification_type=NotificationType.CONSUMPTION_PENDING.value,
                    title="待消课提醒",
                    content=f"排课#{schedule.id}（课程{schedule.course_id}）已到上课时间，"
                            f"请在下课后确认消课。可在待办列表中查看和操作。",
                    ref_id=schedule.id,
                    ref_type="schedule",
                )

                add_log("info",
                        f"排课#{schedule.id} 调度完成：{student_count} 条待办 + 上课提醒 + 待消课提醒 已发送",
                        module="Scheduler", schedule_id=schedule.id,
                        student_count=student_count)

    except Exception as e:
        add_log("error", f"调度器执行失败: {e}", module="Scheduler")
        import traceback
        traceback.print_exc()


async def _send_day_before_reminder():
    """
    每天跑一次：查明天的排课，给学生和家长发"明天有课"通知。
    建议在每天 18:00 触发。
    """
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_dow = tomorrow.isoweekday()

    try:
        async with AsyncDatabase.get_session() as session:
            schedule_dao = ScheduleDao(session)
            schedules = await schedule_dao.find_all(
                day_of_week=tomorrow_dow,
                status=ScheduleActiveStatus.ACTIVE.value,
            )
            if not schedules:
                return

            ss_dao = StudentScheduleDao(session)
            notif_dao = NotificationDao(session)
            course_dao = CourseDao(session)
            parent_dao = ParentStudentDao(session)

            for schedule in schedules:
                course_name = f"课程{schedule.course_id}"
                course = await course_dao.get_by_id(schedule.course_id)
                if course:
                    course_name = course.course_name

                assignments = await ss_dao.get_schedule_students(schedule.id)
                for ass in assignments:
                    student_name = ass.student.real_name if ass.student else f"学生{ass.student_id}"
                    time_str = f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}"

                    # 通知学生
                    if not await notif_dao.notification_exists(
                        ass.student_id, NotificationType.CLASS_REMINDER_DAY_BEFORE.value, schedule.id
                    ):
                        await notif_dao.create_notification(
                            recipient_id=ass.student_id,
                            recipient_role="STUDENT",
                            notification_type=NotificationType.CLASS_REMINDER_DAY_BEFORE.value,
                            title="明天有课",
                            content=f"明天（{tomorrow}）有一节{course_name}，"
                                    f"上课时间 {time_str}，"
                                    f"教室: {schedule.classroom or '未指定'}，请准时参加。",
                            ref_id=schedule.id,
                            ref_type="schedule",
                        )

                    # 通知学生的所有家长
                    parents = await parent_dao.get_student_parents(ass.student_id)
                    for parent in parents:
                        if not await notif_dao.notification_exists(
                            parent.parent_id, NotificationType.CLASS_REMINDER_DAY_BEFORE.value, schedule.id
                        ):
                            await notif_dao.create_notification(
                                recipient_id=parent.parent_id,
                                recipient_role="PARENT",
                                notification_type=NotificationType.CLASS_REMINDER_DAY_BEFORE.value,
                                title="孩子明天有课",
                                content=f"{student_name} 明天（{tomorrow}）有一节{course_name}，"
                                        f"上课时间 {time_str}，"
                                        f"教室: {schedule.classroom or '未指定'}。",
                                ref_id=schedule.id,
                                ref_type="schedule",
                            )

            add_log("info",
                    f"明天上课提醒已发送：{len(schedules)} 个排课",
                    module="Scheduler")

    except Exception as e:
        add_log("error", f"明天上课提醒失败: {e}", module="Scheduler")
        import traceback
        traceback.print_exc()


async def _send_hour_before_reminder():
    """
    每分钟跑一次：查1小时后开始的排课，给学生和家长发"快上课了"通知。
    """
    now = datetime.now()
    today = date.today()
    current_day = now.isoweekday()
    # 1小时后的时间
    target_time = time(now.hour, now.minute)
    target_dt = now + timedelta(hours=1)
    target_hour_time = time(target_dt.hour, target_dt.minute)

    try:
        async with AsyncDatabase.get_session() as session:
            schedule_dao = ScheduleDao(session)
            schedules = await schedule_dao.find_all(
                day_of_week=current_day,
                status=ScheduleActiveStatus.ACTIVE.value,
            )

            # 筛选：start_time 在 1 小时后 ±1 分钟内
            matching = [
                s for s in schedules
                if s.start_time.hour == target_hour_time.hour
                and s.start_time.minute == target_hour_time.minute
            ]
            if not matching:
                return

            ss_dao = StudentScheduleDao(session)
            notif_dao = NotificationDao(session)
            course_dao = CourseDao(session)
            parent_dao = ParentStudentDao(session)

            for schedule in matching:
                course_name = f"课程{schedule.course_id}"
                course = await course_dao.get_by_id(schedule.course_id)
                if course:
                    course_name = course.course_name
                time_str = f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}"

                assignments = await ss_dao.get_schedule_students(schedule.id)
                for ass in assignments:
                    student_name = ass.student.real_name if ass.student else f"学生{ass.student_id}"

                    # 通知学生
                    if not await notif_dao.notification_exists(
                        ass.student_id, NotificationType.CLASS_REMINDER_HOUR_BEFORE.value, schedule.id
                    ):
                        await notif_dao.create_notification(
                            recipient_id=ass.student_id,
                            recipient_role="STUDENT",
                            notification_type=NotificationType.CLASS_REMINDER_HOUR_BEFORE.value,
                            title="上课提醒",
                            content=f"{course_name} 将在1小时后（{time_str}）开始，"
                                    f"教室: {schedule.classroom or '未指定'}，请准备上课。",
                            ref_id=schedule.id,
                            ref_type="schedule",
                        )

                    # 通知家长
                    parents = await parent_dao.get_student_parents(ass.student_id)
                    for parent in parents:
                        if not await notif_dao.notification_exists(
                            parent.parent_id, NotificationType.CLASS_REMINDER_HOUR_BEFORE.value, schedule.id
                        ):
                            await notif_dao.create_notification(
                                recipient_id=parent.parent_id,
                                recipient_role="PARENT",
                                notification_type=NotificationType.CLASS_REMINDER_HOUR_BEFORE.value,
                                title="孩子快上课了",
                                content=f"{student_name} 的{course_name}将在1小时后（{time_str}）开始，"
                                        f"教室: {schedule.classroom or '未指定'}。",
                                ref_id=schedule.id,
                                ref_type="schedule",
                            )

    except Exception as e:
        add_log("error", f"课前1小时提醒失败: {e}", module="Scheduler")
        import traceback
        traceback.print_exc()


def init_scheduler() -> AsyncIOScheduler:
    """初始化并启动后台调度器（在 main.py lifespan 中调用）"""
    global scheduler

    if scheduler is not None:
        add_log("info", "调度器已初始化，跳过重复启动", module="Scheduler")
        return scheduler

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _check_and_create_todos,
        trigger="cron",
        minute="*",
        id="class_reminder_and_todo_generator",
        name="每分钟检查排课 → 生成待办 + 发送上课提醒",
        max_instances=1,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        _send_hour_before_reminder,
        trigger="cron",
        minute="*",
        id="hour_before_reminder",
        name="每分钟检查1小时后开始的排课 → 给学生+家长发提醒",
        max_instances=1,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        _send_day_before_reminder,
        trigger="cron",
        hour="18",
        minute="7",
        id="day_before_reminder",
        name="每天18:00 → 查明天排课 → 给学生+家长发明天的课提醒",
        max_instances=1,
    )
    scheduler.start()

    # 启动时立即执行一次补偿扫描
    import asyncio
    asyncio.ensure_future(_catch_up_today())

    add_log("info", "✅ 后台调度器已启动（待办生成 + 课前1h提醒 + 前一天18:00提醒）", module="Scheduler")
    return scheduler


async def _catch_up_today():
    """
    启动补偿：扫描今天 start_time <= 当前时间 的排课，
    把没生成待办的补上。解决服务器在排课时间点未运行导致漏生成的问题。
    """
    now = datetime.now()
    today = date.today()
    current_day = now.isoweekday()
    current_time = time(now.hour, now.minute)

    try:
        async with AsyncDatabase.get_session() as session:
            schedule_dao = ScheduleDao(session)

            schedules = await schedule_dao.find_all(
                day_of_week=current_day,
                status=ScheduleActiveStatus.ACTIVE.value,
            )

            # 筛选：start_time <= 当前时间（已开课的排课）
            pending = [
                s for s in schedules
                if s.start_time <= current_time
            ]

            if not pending:
                add_log("info", "启动补偿：今天没有已到时间的排课需要补待办", module="Scheduler")
                return

            todo_dao = TeacherTodoDao(session)
            ss_dao = StudentScheduleDao(session)
            sc_dao = StudentCourseDao(session)
            notif_dao = NotificationDao(session)
            course_dao = CourseDao(session)

            # 预加载课程名映射
            course_names: dict[int, str] = {}
            for s in pending:
                if s.course_id not in course_names:
                    course = await course_dao.get_by_id(s.course_id)
                    course_names[s.course_id] = course.course_name if course else f"课程{s.course_id}"

            missed_count = 0

            for schedule in pending:
                already_exists = await todo_dao.todo_exists(schedule.id, today)
                if already_exists:
                    continue

                # 找到分配到这节课的学生
                assignments = await ss_dao.get_schedule_students(schedule.id)
                student_count = 0

                for ass in assignments:
                    student_name = ass.student.real_name if ass.student else f"学生{ass.student_id}"

                    enrollment = await sc_dao.get_by_student_and_course(ass.student_id, schedule.course_id)
                    if not enrollment or enrollment.status != "active":
                        continue
                    if not enrollment.remaining_lessons or enrollment.remaining_lessons <= 0:
                        continue

                    course_name = course_names.get(schedule.course_id, f"课程{schedule.course_id}")
                    await todo_dao.create_todo(
                        teacher_id=schedule.teacher_id,
                        schedule_id=schedule.id,
                        course_id=schedule.course_id,
                        student_id=ass.student_id,
                        todo_date=today,
                        title=f"待消课：{student_name} - {course_name} {today} {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}",
                        detail=(
                            f"学生剩余 {enrollment.remaining_lessons} 课时，"
                            f"教室: {schedule.classroom or '未指定'}"
                        ),
                    )
                    student_count += 1

                    # 补发上课提醒给学生
                    await notif_dao.create_notification(
                        recipient_id=ass.student_id,
                        recipient_role="STUDENT",
                        notification_type=NotificationType.CLASS_REMINDER.value,
                        title="上课提醒",
                        content=f"您有一节{course_name} 即将在 {schedule.start_time} 开始，"
                                f"教室: {schedule.classroom or '未指定'}，请准时参加。",
                        ref_id=schedule.id,
                        ref_type="schedule",
                    )

                if student_count > 0:
                    # 教师上课提醒
                    await notif_dao.create_notification(
                        recipient_id=schedule.teacher_id,
                        recipient_role="TEACHER",
                        notification_type=NotificationType.CLASS_REMINDER.value,
                        title="上课提醒",
                        content=f"您有一节排课#{schedule.id}（课程{schedule.course_id}）"
                                f"将在 {schedule.start_time} 开始，"
                                f"教室: {schedule.classroom or '未指定'}，请准备上课。",
                        ref_id=schedule.id,
                        ref_type="schedule",
                    )
                    # 教师待消课提醒
                    await notif_dao.create_notification(
                        recipient_id=schedule.teacher_id,
                        recipient_role="TEACHER",
                        notification_type=NotificationType.CONSUMPTION_PENDING.value,
                        title="待消课提醒",
                        content=f"排课#{schedule.id}（课程{schedule.course_id}）已到上课时间，"
                                f"请在下课后确认消课。可在待办列表中查看和操作。",
                        ref_id=schedule.id,
                        ref_type="schedule",
                    )
                    missed_count += 1
                    add_log("info",
                            f"补偿：排课#{schedule.id} 补生成 {student_count} 条待办 + 通知",
                            module="Scheduler", schedule_id=schedule.id)

            add_log("info",
                    f"启动补偿完成：{missed_count} 个排课补生成待办",
                    module="Scheduler")

    except Exception as e:
        add_log("error", f"启动补偿执行失败: {e}", module="Scheduler")
        import traceback
        traceback.print_exc()


def shutdown_scheduler():
    """关闭调度器（在 main.py lifespan 退出时调用）"""
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        add_log("info", "🛑 后台调度器已关闭", module="Scheduler")
