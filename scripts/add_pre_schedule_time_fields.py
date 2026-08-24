"""
scripts/add_pre_schedule_time_fields.py
迁移脚本：给 pre_schedule 表补结构化时间字段

背景：preferred_time 以前是自由文本（如"周一 09:00-10:30"），冲突检查靠脆弱正则，
解析失败静默跳过会漏检冲突。现在改成提交时解析一次，存 day_of_week/start_time/end_time
三个结构化字段，冲突检查直接读字段。

本脚本做了两件事（都幂等，重复跑不会报错）：
1. 加列：day_of_week(SMALLINT)、start_time(TIME)、end_time(TIME)
2. 回填：把已有 pre_schedule 的 preferred_time 解析后写入结构化字段
"""
import sys, asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import text
from core.database import AsyncDatabase
from core import settings
from core.service.utils import parse_preferred_time


async def main():
    AsyncDatabase.init(database_url=settings.DB_URI_TEST)
    async with AsyncDatabase.get_session() as session:
        # 1. 加列（幂等）
        await session.execute(text("ALTER TABLE pre_schedule ADD COLUMN IF NOT EXISTS day_of_week SMALLINT"))
        await session.execute(text("ALTER TABLE pre_schedule ADD COLUMN IF NOT EXISTS start_time TIME"))
        await session.execute(text("ALTER TABLE pre_schedule ADD COLUMN IF NOT EXISTS end_time TIME"))

        # 2. 回填：把已有 preferred_time 解析成结构化时间
        rows = (await session.execute(
            text("SELECT id, preferred_time FROM pre_schedule WHERE preferred_time IS NOT NULL")
        )).fetchall()
        filled = 0
        for row in rows:
            parsed = parse_preferred_time(row.preferred_time)
            if parsed is None:
                continue
            await session.execute(
                text("UPDATE pre_schedule SET day_of_week=:d, start_time=:s, end_time=:e WHERE id=:id"),
                {"d": parsed["day_of_week"], "s": parsed["start_time"], "e": parsed["end_time"], "id": row.id},
            )
            filled += 1

        await session.commit()
        print(f"✅ 结构化时间字段已添加，回填 {filled} 条记录")
    await AsyncDatabase.close()


if __name__ == "__main__":
    asyncio.run(main())
