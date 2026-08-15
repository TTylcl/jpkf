"""
test_user_dao_real.py
用真实数据库数据测试UserDao
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def test_with_real_data():
    """用真实数据测试UserDao"""
    print("🧪 用真实数据测试UserDao...")
    
    try:
        # 导入依赖
       
        from core.database import AsyncDatabase
        from dal.dao.user_dao import UserDao
        from dal.models.enums import UserType
        TEST_PG_URI = "postgresql+asyncpg://postgres:123456@127.0.0.1:5432/test_database"
        # 1. 初始化数据库
        print("1. 初始化数据库连接...")
        AsyncDatabase.init(TEST_PG_URI)
        
        # 2. 创建DAO实例
        print("2. 创建UserDao实例...")
        async with AsyncDatabase.get_session() as session:
            user_dao = UserDao(session=session)
            
            # 3. 测试get_by_id - 查询admin001
            print("3. 测试get_by_id() - 查询admin001...")
            admin = await user_dao.get_by_id(1)
            if admin:
                print(f"   ✅ 查询成功: user_id={admin['user_id']}, username={admin['username']}, real_name={admin['real_name']}")
            else:
                print("   ⚠️  admin001不存在")
            
             # 4. 测试get_by_username - 查询teacher001
            print("4. 测试get_by_username() - 查询teacher001...")
            teacher = await user_dao.get_by_username("teacher001")
            if teacher:
                # ✅ 使用get方法安全访问
                print(f"   ✅ 查询成功: user_id={teacher.get('user_id')}, "
                      f"real_name={teacher.get('real_name')}, "
                      f"phone={teacher.get('phone', '[敏感字段未返回]')}, "
                      f"email={teacher.get('email', '[敏感字段未返回]')}")
            else:
                print("   ⚠️  teacher001不存在")
            
            # 5. 测试get_by_phone - 查询13800000002（需要敏感信息）
            print("5. 测试get_by_phone() - 查询13800000002...")
            # 注意：get_by_phone内部调用find_one，也不会返回敏感信息
            teacher_by_phone = await user_dao.get_by_phone("13800000002")
            if teacher_by_phone:
                print(f"   ✅ 查询成功: username={teacher_by_phone.get('username')}, "
                      f"real_name={teacher_by_phone.get('real_name')}")
            else:
                print("   ⚠️  手机号13800000002不存在")
            
            # 6. 测试get_by_email - 查询li@music.com（需要敏感信息）
            print("6. 测试get_by_email() - 查询li@music.com...")
            teacher_by_email = await user_dao.get_by_email("li@music.com")
            if teacher_by_email:
                print(f"   ✅ 查询成功: username={teacher_by_email.get('username')}, "
                      f"real_name={teacher_by_email.get('real_name')}")
            else:
                print("   ⚠️  邮箱li@music.com不存在")
            
            # 7. 测试find_one - 组合查询
            print("7. 测试find_one() - 组合查询...")
            student = await user_dao.find_one(username="student001", user_type=UserType.STUDENT.value)
            if student:
                print(f"   ✅ 查询成功: real_name={student['real_name']}, email={student['email']}")
            else:
                print("   ⚠️  student001不存在")
            
            # 8. 测试find_all - 查询所有老师
            print("8. 测试find_all() - 查询所有老师...")
            teachers = await user_dao.find_all(user_type=UserType.TEACHER.value, limit=10)
            print(f"   ✅ 查询成功: 找到{len(teachers)}个老师")
            for i, t in enumerate(teachers[:3]):  # 只显示前3个
                print(f"      {i+1}. {t['real_name']} ({t['username']})")
            
            # 9. 测试list_teachers - 业务方法
            print("9. 测试list_teachers() - 业务方法...")
            teachers_list = await user_dao.list_teachers(limit=10)
            print(f"   ✅ 查询成功: 找到{len(teachers_list)}个老师")
            
            # 10. 测试list_students - 业务方法
            print("10. 测试list_students() - 业务方法...")
            students_list = await user_dao.list_students(limit=10)
            print(f"   ✅ 查询成功: 找到{len(students_list)}个学生")
            
            # 11. 测试search_users - 模糊搜索
            print("11. 测试search_users() - 模糊搜索'老师'...")
            search_results = await user_dao.search_users(keyword="老师", limit=10)
            print(f"   ✅ 搜索成功: 找到{len(search_results)}个结果")
            for i, r in enumerate(search_results[:3]):
                print(f"      {i+1}. {r['real_name']} ({r['username']})")
            
            # 12. 测试search_users - 模糊搜索'小'
            print("12. 测试search_users() - 模糊搜索'小'...")
            search_results = await user_dao.search_users(keyword="小", limit=10)
            print(f"   ✅ 搜索成功: 找到{len(search_results)}个结果")
            for r in search_results:
                print(f"      - {r['real_name']} ({r['username']})")
            
            # 13. 测试exists_by_username
            print("13. 测试exists_by_username()...")
            exists_admin = await user_dao.exists_by_username("admin001")
            exists_nonexist = await user_dao.exists_by_username("nonexistuser")
            print(f"   ✅ admin001存在: {exists_admin}")
            print(f"   ✅ nonexistuser不存在: {not exists_nonexist}")
            
            # 14. 测试exists_by_phone
            print("14. 测试exists_by_phone()...")
            exists_phone = await user_dao.exists_by_phone("13800000001")
            exists_nonexist_phone = await user_dao.exists_by_phone("11111111111")
            print(f"   ✅ 13800000001存在: {exists_phone}")
            print(f"   ✅ 11111111111不存在: {not exists_nonexist_phone}")
            
            # 15. 测试count
            print("15. 测试count()...")
            teacher_count = await user_dao.count(user_type=UserType.TEACHER.value)
            student_count = await user_dao.count(user_type=UserType.STUDENT.value)
            admin_count = await user_dao.count(user_type=UserType.ADMIN.value)
            print(f"   ✅ 老师数量: {teacher_count}")
            print(f"   ✅ 学生数量: {student_count}")
            print(f"   ✅ 管理员数量: {admin_count}")
            
            # 16. 测试分页查询
            print("16. 测试list_teachers_paginated()...")
            paginated_result = await user_dao.list_teachers_paginated(page=1, page_size=2)
            print(f"   ✅ 分页查询成功:")
            print(f"      总记录数: {paginated_result.get('total', 0)}")
            print(f"      当前页: {paginated_result.get('page', 0)}")
            print(f"      每页大小: {paginated_result.get('page_size', 0)}")
            print(f"      总页数: {paginated_result.get('total_pages', 0)}")
            print(f"      当前页数据: {len(paginated_result.get('items', []))}条")
            
            # 17. 测试get_teacher_courses - 查询老师课程
            print("17. 测试get_teacher_courses() - 查询老师课程...")
            # 先找个老师ID
            if teachers_list:
                teacher_id = teachers_list[0]["user_id"]
                courses = await user_dao.get_teacher_courses(teacher_id)
                print(f"   ✅ 查询成功: 老师{teacher_id}有{len(courses)}门课程")
                if courses:
                    for i, c in enumerate(courses[:2]):  # 只显示前2个
                        print(f"      课程{i+1}: {c.get('course_name', '未知')}")
            else:
                print("   ⚠️  没有老师数据，跳过课程查询")
            
            print("\n🎉 所有测试完成！")
            print("=" * 50)
            print("📊 测试总结:")
            print(f"   1. 查询了管理员: {admin is not None}")
            print(f"   2. 查询了老师: {len(teachers)}位")
            print(f"   3. 查询了学生: {len(students_list)}位")
            print(f"   4. 测试了模糊搜索")
            print(f"   5. 测试了分页查询")
            print(f"   6. 测试了存在性检查")
            print(f"   7. 测试了统计功能")
            
            return True
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理数据库连接
        try:
            await AsyncDatabase.close()
        except:
            pass

if __name__ == "__main__":
    # 直接运行测试
    print("=" * 50)
    print("UserDao真实数据测试")
    print("=" * 50)
    
    success = asyncio.run(test_with_real_data())
    
    if success:
        print("\n✅ UserDao所有方法测试通过！")
        sys.exit(0)
    else:
        print("\n❌ UserDao测试失败")
        sys.exit(1)