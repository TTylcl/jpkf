#schemas\rag_schemas.py


from typing import Optional
from pydantic import BaseModel,Field,model_validator


#数据模型
class RagQuery(BaseModel):
    """rag检索参数"""
    # 用户查询文本
    query: str = Field(..., min_length=1, description="用户查询文本")
    # 返回最相似的k个结果
    top_k: int = Field(default=5,ge=1,le=20)    
    # 过滤条件   
    source_filter: Optional[str] = None
    # 相似度阈值
    distance_threshold: float = Field(default=0.7, ge=0.0, le=2.0) # 参数说明 defalut=0.7 阈值 ge=0.0 le=2.0  阈值越小越相似  le=1.0 阈值越高越不相似
    
    @model_validator(mode="after")
    def validate_query(self):
        """ 去除首尾空格后不能为空"""
        if not self.query.strip() :
            raise ValueError("查询文本不能为空")
        return self

class RagDocument(BaseModel):
    """单条检索结果"""
    # 文本片段
    chunk_text: str
    # 文本片段来源
    source: str
    # 文本片段索引
    chunk_index: int
    # 相似度
    distance: float


class RagResult(BaseModel):
    """RAG 检索响应"""
    # 检索结果
    documents: list[RagDocument] = Field(default_factory=list)
    # 上下文
    context: str = ""
    # 检索总耗时
    total_found: int = 0
    # 检索总耗时
    total_used: int = 0    