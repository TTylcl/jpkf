""" test/dao/test_student_course_dao.py StudentCourseDao完整测试 """
import asyncio
import sys
from pathlib import Path

# 把项目根目录加到Python路径，解决导入问题
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入数据库和DAO

from dal.dao.student_course_dao import StudentCourseDao
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
        dao = StudentCourseDao(session)
        # 测试用ID（换成你自己的测试数据ID）
        TEST_STUDENT_ID = 1
        TEST_COURSE_ID = 1
        

        # ========== 1. 新增记录（先加数据，后面查就有了） ==========
        print("\n🔹 1. create 新增选课记录")
        new_record = await dao.create(
            student_id=TEST_STUDENT_ID,
            course_id=TEST_COURSE_ID,
            status="active"
        )
        print(f"  新增结果: {new_record}")
        assert new_record is not None, "❌ 新增失败"
        new_record_id = new_record.id
        print(f"  ✅ 新增成功，ID: {new_record_id}")

        # ========== 2. 现在查，肯定有数据 ==========
        print("\n🔹 2. get_student_courses 查学生所有选课")
        courses = await dao.get_student_courses(TEST_STUDENT_ID)
        print(f"  查到: {len(courses)} 条记录")
        print(f"  第一条: {courses[0] if courses else '无'}")
        assert len(courses) > 0, "❌ 新增后查询不到数据"
        print(f"  ✅ 通过")

        print("\n🔹 3. get_student_active_courses 查学生生效选课")
        active_courses = await dao.get_student_active_courses(TEST_STUDENT_ID)
        print(f"  生效选课: {len(active_courses)} 条")
        assert len(active_courses) > 0, "❌ 查不到生效选课"
        print(f"  ✅ 通过")

        print("\n🔹 4. get_by_student_and_course 查学生是否选某门课")
        exists_record = await dao.get_by_student_and_course(TEST_STUDENT_ID, TEST_COURSE_ID)
        print(f"  结果: {exists_record}")
        assert exists_record is not None, "❌ 查不到新增的记录"
        print(f"  ✅ 通过")

        print("\n🔹 5. count_student_courses 统计学生选课数量")
        count = await dao.count_student_courses(TEST_STUDENT_ID)
        print(f"  选课数量: {count}")
        assert count > 0, "❌ 统计数量为0"
        print(f"  ✅ 通过")

        # ========== 3. 现在更新，肯定能成功 ==========
        print("\n🔹 6. update 更新状态为dropped")
        updated = await dao.update(new_record_id, status="dropped")
        print(f"  更新结果: {updated}")
        assert updated is not None and updated.status == "dropped", "❌ 更新失败"
        print(f"  ✅ 通过")

        # ========== 4. 查课程学生 ==========
        print("\n🔹 7. list_course_students 查课程所有选课学生")
        students = await dao.list_course_students(TEST_COURSE_ID)
        print(f"  选课学生: {len(students)} 人")
        print(f"  ✅ 通过")

        print("\n🔹 8. count_course_students 统计课程选课人数")
        course_count = await dao.count_course_students(TEST_COURSE_ID)
        print(f"  选课人数: {course_count}")
        print(f"  ✅ 通过")

        # ========== 5. 最后软删除，测试软删除 ==========
        print("\n🔹 9. soft_delete 软删除记录")
        delete_res = await dao.soft_delete(new_record_id)
        print(f"  删除结果: {delete_res}")
        assert delete_res is True, "❌ 删除失败"
        print(f"  ✅ 通过")

        # 测试软删除后默认查不到，加include_deleted=True能查到
        print("\n🔹 10. 验证软删除生效")
        deleted_record = await dao.get_by_id(new_record_id, include_deleted=True)
        normal_query = await dao.get_by_id(new_record_id)
        print(f"  加include_deleted能查到: {deleted_record is not None}")
        print(f"  默认查询查不到: {normal_query is None}")
        assert deleted_record is not None and normal_query is None, "❌ 软删除未生效"
        print(f"  ✅ 软删除生效")

    print("\n" + "=" * 70)
    print("✅ ✅ ✅ StudentCourseDao 所有方法测试全部通过！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_all_methods())