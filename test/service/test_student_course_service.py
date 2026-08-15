"""
StudentCourseService 集成测试
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import AsyncDatabase
from core.context import CTX
from service.student_course_service import StudentCourseService

# 你的 PostgreSQL 测试库
TEST_PG_URI = "postgresql+asyncpg://postgres:123456@127.0.0.1:5434/test_database"


def build_test_ctx(user_id: int, user_role: str, agent_role: str, session) -> CTX:
    """构建测试用CTX"""
    return CTX(
        user_id=user_id,
        user_role=user_role,
        agent_role=agent_role,
        trace_id=f"test_student_course_{asyncio.get_event_loop().time()}",
        wx_openid="",
        session=session,  # ✅ 关键：session必须传进去
    )


def get_student_course_service():
    """构建StudentCourseService实例"""
    return StudentCourseService()


async def test_enroll_student():
    """测试1：学生报名课程"""
    print("🧪 测试enroll_student - 学生报名...")

    async with AsyncDatabase.get_session() as session:
        service = get_student_course_service()
        ctx = build_test_ctx(
            user_id=1,
            user_role="admin",
            agent_role="edu_admin_agent",
            session=session
        )

        # 用真实存在的测试数据（学生ID=6，课程ID=3）
        result = await service.enroll_student(
            ctx=ctx,
            student_id=6,
            course_id=3
        )

        print(f"  success: {result.success}")
        print(f"  code: {result.code}")
        print(f"  message: {result.message}")
        print(f"  data: {result.data}")
        if result.data:
            print(f"  选课记录ID: {result.data.id}")

        if not result.success:
            print("  ❌ 报名失败")
            return False

        print("  ✅ enroll_student测试通过")
        return True


async def test_enroll_duplicate():
    """测试2：重复报名应该报错409"""
    print("🧪 测试enroll_duplicate - 重复报名...")

    async with AsyncDatabase.get_session() as session:
        service = get_student_course_service()
        ctx = build_test_ctx(
            user_id=1,
            user_role="admin",
            agent_role="edu_admin_agent",
            session=session
        )

        # 第一次报名
        result1 = await service.check_enrollment(ctx=ctx, student_id=6, course_id=1)
        print(f"result1: success={result1.success}, code={result1.code}, message={result1.message}, data={result1.data}")

        if result1.success and result1.data is not None:
            enrolled = result1.data.enrolled
            print(f"  检查课程1: enrolled={enrolled}")
            assert enrolled is True  # 根据数据，应该是 True
        else:
            print(f"  查询失败或数据为空: {result1.message}")

        # 第二次报名应该报错
        result2 = await service.enroll_student(ctx=ctx, student_id=6, course_id=2)
        print(f"  第二次报名: success={result2.success}, code={result2.code}")

        if result2.success or result2.code != 409:
            print("  ❌ 重复报名应该返回409")
            return False

        print("  ✅ enroll_duplicate测试通过")
        return True


async def test_check_enrollment():
    """测试3：检查是否已报名"""
    print("🧪 测试check_enrollment - 检查报名状态...")

    async with AsyncDatabase.get_session() as session:
        service = get_student_course_service()
        ctx = build_test_ctx(
            user_id=1,
            user_role="admin",
            agent_role="edu_admin_agent",
            session=session
        )

        # 检查已报名的课程
        result1 = await service.check_enrollment(ctx=ctx, student_id=6, course_id=1)
        print(f"  检查课程1: success={result1.success}, enrolled={result1.data.enrolled}")

        # 检查未报名的课程
        result2 = await service.check_enrollment(ctx=ctx, student_id=6, course_id=999)
        print(f"  检查课程999: success={result2.success}, enrolled={result2.data.enrolled}")

        if not result1.success or not result2.success:
            print("  ❌ check_enrollment失败")
            return False

        print("  ✅ check_enrollment测试通过")
        return True


async def test_get_my_courses():
    """测试4：获取学生的所有选课"""
    print("🧪 测试get_my_courses - 获取学生选课列表...")

    async with AsyncDatabase.get_session() as session:
        service = get_student_course_service()
        ctx = build_test_ctx(
            user_id=6,
            user_role="student",
            agent_role="student_agent",
            session=session
        )

        result = await service.get_my_courses(ctx=ctx, student_id=6)

        print(f"  success: {result.success}")
        print(f"  code: {result.code}")

        if result.data:
            print(f"  选课数量: {len(result.data)}")
            for c in result.data[:3]:  # 显示前3个
                print(f"  - 课程ID: {c.course_id}")

        if not result.success:
            print("  ❌ get_my_courses失败")
            return False

        print("  ✅ get_my_courses测试通过")
        return True


async def test_drop_course():
    """测试5：学生退课"""
    print("🧪 测试drop_course - 学生退课...")

    async with AsyncDatabase.get_session() as session:
        service = get_student_course_service()
        ctx = build_test_ctx(
            user_id=1,
            user_role="admin",
            agent_role="edu_admin_agent",
            session=session
        )

        # 先报一门新课
        await service.enroll_student(ctx=ctx, student_id=6, course_id=3)

        # 再退课
        result = await service.drop_course(ctx=ctx, student_id=6, course_id=3)

        print(f"  success: {result.success}")
        print(f"  code: {result.code}")
        print(f"  message: {result.message}")

        if not result.success:
            print("  ❌ 退课失败")
            return False

        # 检查是否已退课
        check_result = await service.check_enrollment(ctx=ctx, student_id=6, course_id=3)
        if check_result.data.enrolled:
            print("  ❌ 退课后应该显示未报名")
            return False

        print("  ✅ drop_course测试通过")
        return True


async def test_drop_nonexistent_enrollment():
    """测试6：退未选的课程应该报错404"""
    print("🧪 测试drop_nonexistent_enrollment - 退未选的课程...")

    async with AsyncDatabase.get_session() as session:
        service = get_student_course_service()
        ctx = build_test_ctx(
            user_id=1,
            user_role="admin",
            agent_role="edu_admin_agent",
            session=session
        )

        # 退一门从未选过的课
        result = await service.drop_course(ctx=ctx, student_id=6, course_id=9999)

        print(f"  success: {result.success}")
        print(f"  code: {result.code}")
        print(f"  message: {result.message}")

        if result.success or result.code != 404:
            print("  ❌ 退未选的课程应该返回404")
            return False

        print("  ✅ drop_nonexistent_enrollment测试通过")
        return True


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("StudentCourseService 完整测试")
    print("=" * 60)

    # 数据库初始化一次
    AsyncDatabase.init(TEST_PG_URI)
    print("✅ 数据库连接初始化成功")

    tests = [
        ("enroll_student", test_enroll_student),
        ("enroll_duplicate", test_enroll_duplicate),
        ("check_enrollment", test_check_enrollment),
        ("get_my_courses", test_get_my_courses),
        ("drop_course", test_drop_course),
        ("drop_nonexistent_enrollment", test_drop_nonexistent_enrollment),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🔍 开始测试: {test_name}")
        try:
            success = await test_func()
        except Exception as e:
            print(f"  💥 异常: {e}")
            import traceback
            traceback.print_exc()
            success = False

        results.append((test_name, success))

    # 打印测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name:35} {status}")
        if success:
            passed += 1

    print(f"\n总计: {len(tests)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {len(tests) - passed} 个")

    # 关闭数据库
    await AsyncDatabase.close()

    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    if success:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 有测试失败")
        sys.exit(1)