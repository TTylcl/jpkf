""" ScheduleService 集成测试 - 修复版 """

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import AsyncDatabase
from core.context import CTX
from service.schedule_service import ScheduleService
from dal.dao.schedule_dao import ScheduleDao


def build_test_ctx(user_id: int, user_role: str, agent_role: str, session) -> CTX:
    """构建测试用CTX"""
    return CTX(
        user_id=user_id,
        user_role=user_role,
        agent_role=agent_role,
        trace_id=f"test_schedule_{asyncio.get_event_loop().time()}",
        wx_openid="",
        session=session,  # ✅ 关键：session必须传进去
    )


def get_schedule_service():
    """构建ScheduleService实例"""
    return ScheduleService()


async def test_query_schedules_by_teacher():
    """测试1：按老师查询排课"""
    print("🧪 测试query_schedules - 按老师查询...")
    
    async with AsyncDatabase.get_session() as session:
        service = get_schedule_service()
        ctx = build_test_ctx(
            user_id=1, 
            user_role="admin", 
            agent_role="edu_admin_agent",
            session=session
        )
        
        # 查询老师ID=2的所有排课
        result = await service.query_schedules(
            ctx=ctx,
            teacher_id=2,
            page=1,
            page_size=20
        )
        
        print(f"  success: {result.success}")
        print(f"  code: {result.code}")
        print(f"  message: {result.message}")
        
        if result.data:
            print(f"  排课数量: {result.data.total}")
            for s in result.data.items[:3]:  # 显示前3个
                print(f"    - 周{s.day_of_week} {s.start_time}-{s.end_time}")
        
        if not result.success:
            print("  ❌ 查询失败")
            return False
        
        print("  ✅ query_schedules测试通过")
        return True


async def test_query_schedules_by_day():
    """测试2：按星期几查询排课"""
    print("🧪 测试query_schedules - 按星期几查询...")
    
    async with AsyncDatabase.get_session() as session:
        service = get_schedule_service()
        ctx = build_test_ctx(
            user_id=1, 
            user_role="admin", 
            agent_role="edu_admin_agent",
            session=session
        )
        
        # 查询周五的所有排课
        result = await service.query_schedules(
            ctx=ctx,
            day_of_week=5,  # 周五
            page=1,
            page_size=20
        )
        
        print(f"  success: {result.success}")
        if result.data:
            print(f"  周五排课数量: {result.data.total}")
        
        if not result.success:
            print("  ❌ 查询失败")
            return False
        
        print("  ✅ 按星期查询测试通过")
        return True


async def test_get_today_schedules():
    """测试3：查询今天的排课"""
    print("🧪 测试get_today_schedules...")
    
    async with AsyncDatabase.get_session() as session:
        service = get_schedule_service()
        ctx = build_test_ctx(
            user_id=6,  # 学生ID=6
            user_role="student", 
            agent_role="student_agent",
            session=session
        )
        
        # 查询学生今天的排课
        result = await service.get_today_schedules(
            ctx=ctx,
            student_id=6
        )
        
        print(f"  success: {result.success}")
        print(f"  code: {result.code}")
        if result.data:
            print(f"  今天排课数量: {len(result.data.items)}")  # ✅ 用 .items 访问实际数据
            for s in result.data.items[:3]:  # 显示前3个
                print(f"    - {s.start_time}-{s.end_time} 教室: {s.classroom}")
        if not result.success:
            print("  ❌ 查询失败")
            return False
        
        print("  ✅ get_today_schedules测试通过")
        return True


async def test_permission_denied():
    """测试4：权限拦截 - 学生不能创建排课"""
    print("🧪 测试permission_denied...")
    
    async with AsyncDatabase.get_session() as session:
        service = get_schedule_service()
        ctx = build_test_ctx(
            user_id=6, 
            user_role="student", 
            agent_role="student_agent",
            session=session
        )
        
        # 学生角色应该没有创建排课的权限
        result = await service.create_schedule(
            ctx=ctx,
            course_id=1,
            teacher_id=2,
            day_of_week=1,
            start_time="09:00",
            end_time="10:30",
            classroom="101"
        )
        
        print(f"  success: {result.success}")
        print(f"  code: {result.code}")
        print(f"  message: {result.message}")
        
        if result.success or result.code != 403:
            print("  ❌ 学生不应该有权限创建排课，应该返回403")
            return False
        
        print("  ✅ permission_denied测试通过")
        return True


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("ScheduleService 完整测试")
    print("=" * 60)
    
 
    print("✅ 数据库连接初始化成功")
    
    tests = [
        ("query_schedules_by_teacher", test_query_schedules_by_teacher),
        ("query_schedules_by_day", test_query_schedules_by_day),
        ("get_today_schedules", test_get_today_schedules),
        ("permission_denied", test_permission_denied),
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
    

    
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    if success:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 有测试失败")
        sys.exit(1)