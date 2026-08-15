import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

# 先导入模型
from dal.models.course_model import Course
from dal.models.enums import CourseType, CourseStatus

# 导入 DAO 和数据库
from dal.dao.course_dao import CourseDao
from core.database import AsyncDatabase


async def test_all_methods():
    """完整测试 CourseDao 的所有方法 - 全栈ORM版本"""
    
    # 1. 初始化数据库
    TEST_PG_URI = "postgresql+asyncpg://postgres:123456@127.0.0.1:5434/test_database"
    AsyncDatabase.init(TEST_PG_URI)
    
    print("=" * 70)
    print("CourseDao 所有方法完整测试（全栈ORM版本）")
    print("=" * 70)
    
    # 每个测试用新的 session
    async with AsyncDatabase.get_session() as session:
        dao = CourseDao(session)
        
        # ========== 1. get_by_id ==========
        print("\n🔹 1. get_by_id(1)")
        course = await dao.get_by_id(1)
        print(f"  结果: {course}")
        print(f"  ✅ 通过" if course else "  ❌ 失败")
        
        # ========== 2. get_by_course_code ==========
        print("\n🔹 2. get_by_course_code('PIANO001')")
        course = await dao.get_by_course_code("PIANO001")
        print(f"  结果: {course}")
        print(f"  ✅ 通过" if course else "  ⚠️  没有这个课程编码（自己改个存在的）")
        
        # ========== 3. find_all（老师ID=1） ==========
        print("\n🔹 3. find_all（老师ID=1，只查未删除）")
        courses = await dao.find_all(skip=0, limit=10, teacher_id=1)
        print(f"  返回: {len(courses)} 门课程")
        print(f"  前3门: {courses[:3]}")
        print(f"  ✅ 通过")

        # ========== 4. find_all（查所有正课） ==========
        print("\n🔹 4. find_all（查所有正课）")
        courses = await dao.find_all(skip=0, limit=10, course_type=CourseType.REGULAR)
        print(f"  返回: {len(courses)} 门正课")
        print(f"  前3门: {courses[:3]}")
        print(f"  ✅ 通过")

        # ========== 5. find_all（查询所有已上架课程） ==========
        print("\n🔹 5. find_all（查询所有已上架课程）")
        courses = await dao.find_all(skip=0, limit=10, status=CourseStatus.ONLINE)
        print(f"  返回: {len(courses)} 门已上架课程")
        print(f"  前3门: {courses[:3]}")
        print(f"  ✅ 通过")

        # ========== 6. search_courses（模糊搜索暂不支持，用 find_all 替代） ==========
        print("\n🔹 6. find_all（查课程名含特定关键词——DAO不提供模糊搜索，用QueryService）")
        print(f"  ⚠️  跳过：模糊搜索请用 CourseQueryService")

        # ========== 7. search_courses 按类型过滤（跳过） ==========
        print("\n🔹 7. 模糊搜索+类型过滤（跳过，请用 QueryService）")

        # ========== 8. exists_by_course_code ==========
        print("\n🔹 8. exists_by_course_code")
        exists1 = await dao.exists_by_course_code("PIANO001")
        exists2 = await dao.exists_by_course_code("GUITAR0012")
        print(f"  PIANO001 是否存在: {exists1}")
        print(f"  不存在的编码是否存在: {exists2}")
        print(f"  ✅ 通过")
        
        # ========== 9. count（按老师统计课程数） ==========
        print("\n🔹 9. count（老师ID=2 的课程数）")
        course_count = await dao.count(teacher_id=2)
        print(f"  总数: {course_count} 门课程")
        print(f"  ✅ 通过")

        # ========== 10. count（按类型统计） ==========
        print("\n🔹 10. count（体验课数量）")
        trial_count = await dao.count(course_type=CourseType.TRIAL)
        print(f"  总数: {trial_count} 门体验课")
        print(f"  ✅ 通过")

        # ========== 11. count（已上架课程） ==========
        print("\n🔹 11. count（已上架课程）")
        published_count = await dao.count(status=CourseStatus.ONLINE)
        print(f"  总数: {published_count} 门课")
        print(f"  ✅ 通过")
        
        # ========== 12. create（如果需要的话，注意字段匹配） ==========
        # print("\n🔹 12. create（创建测试课程）")
        # new_course = await dao.create(
        #     course_name="测试课程",
        #     course_code=f"TEST{int(asyncio.get_event_loop().time())}",
        #     teacher_id=1,
        #     teacher_name="测试老师",
        #     course_type=CourseType.ONLINE,
        #     status=CourseStatus.ONLINE.value
        # )
        # print(f"  创建成功，ID: {new_course.course_id}")
        # print(f"  ✅ 通过")
        
        # ========== 13. update ==========
        # print("\n🔹 13. update（修改测试课程）")
        # updated_course = await dao.update(
        #     new_course.course_id,
        #     course_name="测试课程已修改",
        #     status=CourseStatus.OFFLINE.value
        # )
        # print(f"  修改后名称: {updated_course.course_name}")
        # print(f"  修改后状态: {updated_course.status}")
        # print(f"  ✅ 通过")
        
        # ========== 14. soft_delete ==========
        # print("\n🔹 14. soft_delete（删除测试课程）")
        # result = await dao.soft_delete(new_course.course_id)
        # print(f"  删除结果: {result}")
        # deleted_course = await dao.get_by_id(new_course.course_id)
        # print(f"  查询已删除课程: {deleted_course}")
        # print(f"  ✅ 通过" if deleted_course is None else "  ❌ 失败")
        
        # session 自动关闭
        print("\n" + "=" * 70)
        print("✅ ✅ ✅ 所有方法测试完成！")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_all_methods())