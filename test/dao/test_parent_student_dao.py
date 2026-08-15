import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

# 先导入模型
from dal.models.course_model import Course
from dal.models.enums import ParentRelation

# 导入 DAO 和数据库
from dal.dao.parent_student_dao import ParentStudentDao
from core.database import AsyncDatabase


async def test_all_methods():
    """完整测试 CourseDao 的所有方法 - 全栈ORM版本"""
    
    # 1. 初始化数据库
    TEST_PG_URI = "postgresql+asyncpg://postgres:123456@127.0.0.1:5434/test_database"
    AsyncDatabase.init(TEST_PG_URI)
    
    print("=" * 70)
    print("ParentStudentDao 所有方法完整测试（全栈ORM版本）")
    print("=" * 70)
    
    # 每个测试用新的 session
    async with AsyncDatabase.get_session() as session:
        dao = ParentStudentDao(session)
        TEST_PARENT_ID = 1
        TEST_STUDENT_ID = 1

        # 1. 绑定家长和学生
        print("\n🔹 1. bind 绑定家长和学生")
        bind_record = await dao.bind(
            parent_id=TEST_PARENT_ID,
            student_id=TEST_STUDENT_ID,
            relation=ParentRelation.MOTHER.value,
            
        )
        print(f"  绑定结果: {bind_record}")
        assert bind_record is not None, "❌ 绑定失败"
        bind_id = bind_record.id
        print(f"  ✅ 绑定成功，ID: {bind_id}")

        # 2. 查询家长的学生
        print("\n🔹 2. get_parent_students 查家长绑定的学生")
        students = await dao.get_parent_students(TEST_PARENT_ID)
        print(f"  绑定学生数: {len(students)}")
        assert len(students) > 0, "❌ 查不到绑定学生"
        print(f"  ✅ 通过")

        # 3. 查询学生的家长
        print("\n🔹 3. get_student_parents 查学生的家长")
        parents = await dao.get_student_parents(TEST_STUDENT_ID)
        print(f"  家长数: {len(parents)}")
        assert len(parents) > 0, "❌ 查不到学生家长"
        print(f"  ✅ 通过")

       
        # 1. 查解绑前
        before = await dao.get_by_id(bind_id, include_deleted=True)
        print(f"解绑前deleted_at: {before.deleted_at}")

        # 2. 执行解绑！！！（必须有这一步）
        await dao.unbind(TEST_PARENT_ID, TEST_STUDENT_ID)  # 或者 await dao.soft_delete(bind_id)

        # 3. 查解绑后
        after = await dao.get_by_id(bind_id, include_deleted=True)
        print(f"解绑后deleted_at: {after.deleted_at}")

        # 4. 验证查不到
        unbind_query = await dao.find_one(parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID)
        assert unbind_query is None, "❌ 解绑失败"
        print(f" ✅ 通过")

    print("\n" + "=" * 70)
    print("✅ ✅ ✅ ParentStudentDao 所有方法测试全部通过！")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_all_methods())