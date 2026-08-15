"""
scripts/seed_data.py
种子数据脚本 —— 导入完整的音乐课程测试数据
运行方式：python scripts/seed_data.py
"""
import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")
from datetime import datetime, time
from sqlalchemy import text
from core.database import AsyncDatabase
from core import settings
from dal.models.base_model import Base


async def seed():
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    async with AsyncDatabase.get_session() as session:
        conn = await session.connection()
        await conn.run_sync(Base.metadata.create_all)

        # ── 清空 ──
        for t in ["lesson_consumption","teacher_todo","notification","parent_student",
                  "pre_schedule","student_courses","student_schedule","schedule","chat_message","session_info","course_info"]:
            await session.execute(text(f"DELETE FROM {t}"))
        await session.execute(text(
            "DELETE FROM user_info WHERE user_type IN ('STUDENT','TEACHER','PARENT')"))
        await session.commit()
        print("旧数据已清除")

        now = datetime.now()

        # ── 教师 ──
        await session.execute(text(
            "INSERT INTO user_info (user_id,username,real_name,phone,email,user_type,status) "
            "VALUES (101,'prof_zhou','周明远','13800001001','zhoumy@music.edu','TEACHER',1)"))
        await session.execute(text(
            "INSERT INTO user_info (user_id,username,real_name,phone,email,user_type,status) "
            "VALUES (102,'prof_wu','吴雅芬','13800001002','wuyf@music.edu','TEACHER',1)"))
        await session.execute(text(
            "INSERT INTO user_info (user_id,username,real_name,phone,email,user_type,status) "
            "VALUES (103,'prof_zheng','郑浩然','13800001003','zhenghr@music.edu','TEACHER',1)"))
        await session.execute(text(
            "INSERT INTO user_info (user_id,username,real_name,phone,email,user_type,status) "
            "VALUES (104,'prof_lin','林婉清','13800001004','linwq@music.edu','TEACHER',1)"))
        await session.execute(text(
            "INSERT INTO user_info (user_id,username,real_name,phone,email,user_type,status) "
            "VALUES (105,'prof_chen','陈思远','13800001005','chensy@music.edu','TEACHER',1)"))
        print("5位教师 (101-105)")

        # ── 学生 ──
        students = [
            (201,"赵一辰"),(202,"钱一诺"),(203,"孙子轩"),(204,"李梓涵"),
            (205,"周雨萱"),(206,"吴浩然"),(207,"郑佳怡"),(208,"王铭泽"),
            (209,"冯诗涵"),(210,"陈瑞琪"),(211,"褚雨桐"),(212,"卫志远"),
            (213,"蒋欣妍"),(214,"沈浩宇"),(215,"韩思源"),(216,"杨婉清"),
            (217,"朱俊豪"),(218,"秦晓彤"),(219,"尤逸飞"),(220,"许梦瑶"),
        ]
        for uid,name in students:
            await session.execute(text(
                "INSERT INTO user_info (user_id,username,real_name,phone,user_type,status) VALUES (:u,:n,:n,:p,'STUDENT',1)"
            ),{"u":uid,"n":name,"p":f"1390001{uid-200:03d}"})
        print("20名学生 (201-220)")

        # ── 家长 ──
        parents = [
            (301,"赵建国"),(302,"钱慧芳"),(303,"孙志强"),(304,"李美玲"),
            (305,"周伟民"),(306,"吴秀丽"),(307,"郑建国"),(308,"王丽华"),
            (309,"冯志明"),(310,"陈建国"),(311,"褚晓燕"),(312,"卫建国"),
            (313,"沈月华"),
        ]
        for uid,name in parents:
            await session.execute(text(
                "INSERT INTO user_info (user_id,username,real_name,phone,user_type,status) VALUES (:u,:n,:n,:p,'PARENT',1)"
            ),{"u":uid,"n":name,"p":f"1390002{uid-300:03d}"})
        print("13位家长 (301-313)")

        # ── 课程 ──
        await session.execute(text(
            "INSERT INTO course_info (course_id,course_code,course_name,course_type,teacher_id,teacher_name,description,total_lessons,price,status) "
            "VALUES (1,'PIANO-001','钢琴基础课','REGULAR',101,'周明远','钢琴入门到考级，涵盖哈农/车尔尼/巴赫等经典教材，一对一教学',40,280.00,1)"))
        await session.execute(text(
            "INSERT INTO course_info (course_id,course_code,course_name,course_type,teacher_id,teacher_name,description,total_lessons,price,status) "
            "VALUES (2,'VIO-001','小提琴基础课','REGULAR',103,'郑浩然','小提琴系统教学，从持琴姿势到协奏曲，注重乐感和技巧并重',40,300.00,1)"))
        print("2门音乐课程 (1=钢琴, 2=小提琴)")

        # ── 学生选课 ──
        piano = [201,202,203,204,205,207,208,210,212,214,216,219]
        violin = [206,209,211,213,215,217,218,220]
        for sid in piano:
            p = 30 if sid%2==0 else 20
            r = p - ((sid-200)%8)
            await session.execute(text(
                "INSERT INTO student_courses (student_id,course_id,enrolled_at,status,purchased_lessons,remaining_lessons) "
                "VALUES (:s,1,:now,'active',:p,:r)"
            ),{"s":sid,"now":now,"p":p,"r":r})
        for sid in violin:
            p = 30 if sid%2==0 else 20
            r = p - ((sid-200)%6)
            await session.execute(text(
                "INSERT INTO student_courses (student_id,course_id,enrolled_at,status,purchased_lessons,remaining_lessons) "
                "VALUES (:s,2,:now,'active',:p,:r)"
            ),{"s":sid,"now":now,"p":p,"r":r})
        print("20名学生选课完成")

        # ── 家长绑定 ──
        binds = [
            (301,201,"father"),(301,203,"guardian"),(302,202,"mother"),
            (303,203,"father"),(304,204,"mother"),(305,205,"father"),
            (306,206,"mother"),(307,207,"father"),(307,201,"guardian"),
            (308,208,"mother"),(309,209,"father"),(309,210,"father"),
            (310,210,"father"),(311,211,"mother"),(312,212,"father"),
            (312,213,"father"),(313,214,"mother"),(313,215,"mother"),
            (313,216,"mother"),
        ]
        for p,s,r in binds:
            await session.execute(text(
                "INSERT INTO parent_student (parent_id,student_id,relation) VALUES (:p,:s,:r)"),{"p":p,"s":s,"r":r})
        print(f"{len(binds)}条家长绑定完成")

        # ── 排课 (使用 time 对象) ──
        sched = [
            # Mon
            (1,101,1,time(9,0),time(10,0),"QinFang A"),(1,102,1,time(10,30),time(11,30),"QinFang A"),
            (2,103,1,time(14,0),time(15,0),"QinFang B"),(1,104,1,time(15,30),time(16,30),"QinFang C"),
            (2,104,1,time(17,0),time(18,0),"QinFang B"),
            # Tue
            (1,101,2,time(9,0),time(10,0),"QinFang A"),(2,103,2,time(10,30),time(11,30),"QinFang B"),
            (1,105,2,time(14,0),time(15,0),"QinFang A"),(2,104,2,time(15,30),time(16,30),"QinFang B"),
            (1,102,2,time(17,0),time(18,0),"QinFang C"),
            # Wed
            (1,101,3,time(9,0),time(10,0),"QinFang A"),(2,103,3,time(10,30),time(11,30),"QinFang B"),
            (1,105,3,time(14,0),time(15,0),"QinFang A"),(2,105,3,time(15,30),time(16,30),"QinFang B"),
            (1,102,3,time(17,0),time(18,0),"QinFang C"),
            # Thu
            (1,102,4,time(9,0),time(10,0),"QinFang A"),(1,101,4,time(10,30),time(11,30),"QinFang A"),
            (2,103,4,time(14,0),time(15,0),"QinFang B"),(2,104,4,time(15,30),time(16,30),"QinFang B"),
            (1,105,4,time(17,0),time(18,0),"QinFang C"),
            # Fri
            (1,101,5,time(9,0),time(10,0),"QinFang A"),(2,103,5,time(10,30),time(11,30),"QinFang B"),
            (1,102,5,time(14,0),time(15,0),"QinFang A"),(2,104,5,time(15,30),time(16,30),"QinFang B"),
            (1,105,5,time(17,0),time(18,0),"QinFang C"),
            # Sat
            (1,101,6,time(8,30),time(9,30),"QinFang A"),(2,103,6,time(9,0),time(10,0),"QinFang B"),
            (1,102,6,time(10,0),time(11,0),"QinFang A"),(2,104,6,time(10,30),time(11,30),"QinFang B"),
            (1,105,6,time(14,0),time(15,0),"QinFang C"),(2,105,6,time(15,30),time(16,30),"QinFang B"),
            # Sun
            (1,102,7,time(9,0),time(10,0),"QinFang A"),(2,103,7,time(10,30),time(11,30),"QinFang B"),
            (1,104,7,time(14,0),time(15,0),"QinFang C"),(2,104,7,time(15,30),time(16,30),"QinFang B"),
        ]
        for c,t,d,s,e,r in sched:
            await session.execute(text(
                "INSERT INTO schedule (course_id,teacher_id,day_of_week,start_time,end_time,classroom,status) "
                "VALUES (:c,:t,:d,:s,:e,:r,1)"
            ),{"c":c,"t":t,"d":d,"s":s,"e":e,"r":r})
        await session.commit()
        print(f"{len(sched)}条排课已插入(每天都有钢琴+小提琴课)")

        # ── 学生-排课分配：每个时段至少有一个学生 ──
        # 先查出所有排课ID
        piano_slots = (await session.execute(text(
            "SELECT id, day_of_week FROM schedule WHERE course_id=1 ORDER BY id"
        ))).fetchall()
        violin_slots = (await session.execute(text(
            "SELECT id, day_of_week FROM schedule WHERE course_id=2 ORDER BY id"
        ))).fetchall()

        # 钢琴：20个时段，12个学生，每人至少2次课 → 24个分配，确保覆盖所有20个时段
        piano_students_list = [201,202,203,204,205,207,208,210,212,214,216,219]
        piano_ids = [s[0] for s in piano_slots]
        # 先每人分配一个时段（覆盖12个时段）
        for i, sid in enumerate(piano_students_list):
            await session.execute(text(
                "INSERT INTO student_schedule (student_id, schedule_id) VALUES (:s,:sc)"
            ), {"s": sid, "sc": piano_ids[i]})
        # 再给前8个学生分配第二个时段（覆盖剩余8个时段，共计20个全部覆盖）
        for i in range(8):
            await session.execute(text(
                "INSERT INTO student_schedule (student_id, schedule_id) VALUES (:s,:sc)"
            ), {"s": piano_students_list[i], "sc": piano_ids[12 + i]})
        # 前4个学生再分配第三个时段（凑满24个分配）
        for i in range(4):
            await session.execute(text(
                "INSERT INTO student_schedule (student_id, schedule_id) VALUES (:s,:sc)"
            ), {"s": piano_students_list[i], "sc": piano_ids[(i + 8) % 20]})

        # 小提琴：15个时段，8个学生，每人至少2次课 → 16个分配，加1个覆盖15
        violin_students_list = [206,209,211,213,215,217,218,220]
        violin_ids = [s[0] for s in violin_slots]
        for i, sid in enumerate(violin_students_list):
            await session.execute(text(
                "INSERT INTO student_schedule (student_id, schedule_id) VALUES (:s,:sc)"
            ), {"s": sid, "sc": violin_ids[i % 15]})
        for i in range(7):
            await session.execute(text(
                "INSERT INTO student_schedule (student_id, schedule_id) VALUES (:s,:sc)"
            ), {"s": violin_students_list[i], "sc": violin_ids[(8 + i) % 15]})
        # 前1个学生再给一个（凑满16）
        await session.execute(text(
            "INSERT INTO student_schedule (student_id, schedule_id) VALUES (:s,:sc)"
        ), {"s": violin_students_list[0], "sc": violin_ids[14]})

        await session.commit()
        total_ss = (await session.execute(text("SELECT count(*) FROM student_schedule"))).scalar()
        print(f"{total_ss}条学生-排课绑定完成(每人每周2次课)")

        print("\n种子数据全部导入完成!")
        print("="*50)
        print("  2门音乐课程: 钢琴基础课 / 小提琴基础课")
        print("  5位教师(101-105): 周明远 吴雅芬 郑浩然 林婉清 陈思远")
        print("  20名学生(201-220): 12钢琴 + 8小提琴")
        print("  13位家长(301-313): 含多子女+跨家庭绑定")
        print(f"  {len(sched)}条排课: 每周7天,每天都有课")
        print("="*50)
    await AsyncDatabase.close()

if __name__=="__main__":
    asyncio.run(seed())
