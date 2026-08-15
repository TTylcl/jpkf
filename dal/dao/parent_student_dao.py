"""
dal/dao/parent_student_dao.py
家长-学生关联DAO
"""
from __future__ import annotations

from core.dao.sqlalchemy_base_dao import SqlalchemyBaseDAO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dal.models.parent_student_model import ParentStudent as model

class ParentStudentDao(SqlalchemyBaseDAO):
    """家长学生关联DAO"""
    primary_key = "id"
    deleted_field = "deleted_at"
    
    @property
    def model(self):
        from dal.models.parent_student_model import ParentStudent
        return ParentStudent
    # ==================== 全用基类封装方法，零原生SQL ====================
    async def get_parent_students(self, parent_id: int) -> list[model]:
        """查询家长绑定的所有学生"""
        return await self.find_all(parent_id=parent_id)

    async def get_student_parents(self, student_id: int) -> list[model]:
        """查询学生的所有家长/监护人"""
        return await self.find_all(student_id=student_id)

  
    async def bind(
        self,
        parent_id: int,
        student_id: int,
        relation: str = "guardian",
        is_default: bool = False
    ) -> model:
        """绑定家长和学生（软删自动恢复，避免唯一冲突）"""
        # 先查有没有已经绑定的记录（包括已软删的）
        exist = await self.find_one(
            parent_id=parent_id,
            student_id=student_id,
            include_deleted=True
        )
        if exist:
            # 有记录就恢复软删，更新信息
            exist.relation = relation # 更新关系字段
            exist.deleted_at = None  # 恢复软删
            await self.session.flush()  # 刷新到数据库以获取ID等信息
            await self.session.refresh(exist) # 刷新对象状态
            return exist # 返回原记录（已更新）
            
        # 没有就新增绑定
        return await self.create(
            parent_id=parent_id,
            student_id=student_id,
            relation=relation,
           
        )

    async def unbind(self, parent_id: int, student_id: int) -> bool:
        """解绑家长和学生（软删）"""
        # 1. 先按条件找到绑定记录
        bind_record = await self.find_one(parent_id=parent_id, student_id=student_id)
        if not bind_record:
            return False  # 本来就没绑定，不用删
        # 2. 按记录的主键ID软删
        return await self.soft_delete(bind_record.id)
    async def check_bind_exists(self, parent_id: int, student_id: int) -> bool:
        """检查家长和学生是否已经绑定"""
        return await self.exists(parent_id=parent_id, student_id=student_id)