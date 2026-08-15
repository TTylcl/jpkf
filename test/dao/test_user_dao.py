import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

# 先导入模型

from dal.models.enums import UserType,UserStatus

# 导入 DAO 和数据库
from dal.dao.user_dao import UserDao
from core.database import AsyncDatabase


async def test_all_methods():
    """完整测试 UserDao 的所有方法 - 全栈ORM版本"""
    
    # 1. 初始化数据库
    TEST_PG_URI = "postgresql+asyncpg://postgres:123456@127.0.0.1:5434/test_database"
    AsyncDatabase.init(TEST_PG_URI)
    
    print("=" * 70)
    print("UserDao 所有方法完整测试（全栈ORM版本）")
    print("=" * 70)
    
    # 每个测试用新的 session
    async with AsyncDatabase.get_session() as session:
        dao = UserDao(session)
        
        # ========== 1. get_by_id ==========
        print("\n🔹 1. get_by_id(1)")
        user = await dao.get_by_id(1)
        print(f"  结果: {user}")
        print(f"  ✅ 通过" if user else "  ❌ 失败")
        
        # ========== 2. get_by_username ==========
        print("\n🔹 2. get_by_username('admin001')")
        user = await dao.get_by_username("admin001")
        print(f"  结果: {user}")
        print(f"  ✅ 通过" if user else "  ❌ 失败")
        
        # ========== 3. get_by_phone ==========
        print("\n🔹 3. get_by_phone（用第一个用户的电话）")
        first_user = await dao.get_by_id(1)
        if first_user and hasattr(first_user, 'phone') and first_user.phone:
            user = await dao.get_by_phone(first_user.phone)
            print(f"  查询电话: {first_user.phone}")
            print(f"  结果: {user}")
            print(f"  ✅ 通过" if user else "  ❌ 失败")
        else:
            print("  ⚠️  跳过：第一个用户没有 phone 字段")
        
        # ========== 4. get_by_email ==========
        print("\n🔹 4. get_by_email（用第一个用户的邮箱）")
        if first_user and hasattr(first_user, 'email') and first_user.email:
            user = await dao.get_by_email(first_user.email)
            print(f"  查询邮箱: {first_user.email}")
            print(f"  结果: {user}")
            print(f"  ✅ 通过" if user else "  ❌ 失败")
        else:
            print("  ⚠️  跳过：第一个用户没有 email 字段")
        
        # ========== 5. list_teachers ==========
        print("\n🔹 5. list_teachers（skip=0, limit=10）")
        teachers = await dao.list_teachers(skip=0, limit=10)
        print(f"  返回: {len(teachers)} 位老师")
        print(f"  前3条: {teachers[:3]}")
        print(f"  ✅ 通过")
        
        # ========== 6. list_students ==========
        print("\n🔹 6. list_students（skip=0, limit=10）")
        students = await dao.list_students(skip=0, limit=10)
        print(f"  返回: {len(students)} 位学生")
        print(f"  前3条: {students[:3]}")
        print(f"  ✅ 通过")
        
        # ========== 7. count（统计老师数量） ==========
        print("\n🔹 7. count（统计老师数量）")
        teacher_count = await dao.count(user_type=UserType.TEACHER.value)
        print(f"  总数: {teacher_count} 位老师")
        print(f"  ✅ 通过")

        # ========== 8. count（统计学生数量） ==========
        print("\n🔹 8. count（统计学生数量）")
        student_count = await dao.count(user_type=UserType.STUDENT.value)
        print(f"  总数: {student_count} 位学生")
        print(f"  ✅ 通过")

        # ========== 9. 模糊搜索（跳过，DAO 不提供，请用 UserQueryService） ==========
        print("\n🔹 9. 模糊搜索（跳过，请用 UserQueryService）")

        # ========== 10. 模糊搜索按类型（跳过，请用 UserQueryService） ==========
        print("\n🔹 10. 模糊搜索按类型（跳过，请用 UserQueryService）")

        # ========== 11. exists_by_username ==========
        print("\n🔹 11. exists_by_username")
        exists1 = await dao.exists_by_username("admin001")
        exists2 = await dao.exists_by_username("nonexistent_user_12345")
        print(f"  admin001 是否存在: {exists1}")
        print(f"  不存在的用户是否存在: {exists2}")
        print(f"  ✅ 通过" if exists1 and not exists2 else "  ❌ 失败")
        
        # ========== 12. exists_by_phone ==========
        print("\n🔹 12. exists_by_phone")
        if first_user and hasattr(first_user, 'phone') and first_user.phone:
            exists1 = await dao.exists_by_phone(first_user.phone)
            exists2 = await dao.exists_by_phone("00000000000")
            print(f"  {first_user.phone} 是否存在: {exists1}")
            print(f"  不存在的电话是否存在: {exists2}")
            print(f"  ✅ 通过" if exists1 and not exists2 else "  ❌ 失败")
        else:
            print("  ⚠️  跳过：第一个用户没有 phone 字段")
        
        # ========== 13. 跨表查询（跳过，请用 CourseQueryService） ==========
        print("\n🔹 13. 跨表查询老师课程（跳过，请用 CourseQueryService）")

        # ========== 14. create ==========
        print("\n🔹 14. create（创建测试用户）")
        new_user = await dao.create(
            username=f"test_user_{asyncio.get_event_loop().time()}",  # 用时间戳避免重复
            real_name="测试用户",
            phone=f"138{int(asyncio.get_event_loop().time()):08d}",  # 手机号也用时间戳
            email="test@example.com",
            user_type=UserType.STUDENT,
            status=UserStatus.ENABLE.value
        )
        print(f"  创建成功，ID: {new_user.user_id}")
        print(f"  ✅ 通过")
        
        # ========== 15. update ==========
        print("\n🔹 15. update（修改测试用户）")
        updated_user = await dao.update(
            new_user.user_id,
            real_name="测试用户已修改",
            phone="13800000002"
        )
        print(f"  修改后姓名: {updated_user.real_name}")
        print(f"  修改后电话: {updated_user.phone}")
        print(f"  ✅ 通过")
        
        # ========== 16. soft_delete ==========
        print("\n🔹 16. soft_delete（删除测试用户）")
        result = await dao.soft_delete(new_user.user_id)
        print(f"  删除结果: {result}")
        # 验证删除
        deleted_user = await dao.get_by_id(new_user.user_id)
        print(f"  查询已删除用户: {deleted_user}")
        print(f"  ✅ 通过" if deleted_user is None else "  ❌ 失败")
        
        # session 自动关闭
        print("\n" + "=" * 70)
        print("✅ ✅ ✅ 所有方法测试完成！")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_all_methods())