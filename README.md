# AI 教务客服 Agent 系统

基于 **LangGraph ReAct + Router 架构** 的多角色智能教育客服系统，支持家长查课、课程咨询、预排课审核等场景。

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.4-orange)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-pgvector-blue)](https://www.postgresql.org/)

---

## 🏗️ 架构概览

```
用户消息（微信 / API）
        │
        ▼
┌──────────────────┐
│  permission_check │  ← JWT 鉴权 + 4 角色白名单
└────────┬─────────┘
         │ (通过)
         ▼
┌──────────────────┐
│ prefetch_children │  ← 预加载家长的孩子列表
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ classify_intent   │  ← LLM 结构化分类（3 路意图）
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│            角色 × 意图路由                │
│  6 个专用 Agent，各自独立的 prompt + 工具白名单 │
│                                          │
│  parent × schedule → schedule_agent       │
│  parent × course   → course_rag_agent     │
│  parent × general  → parent_service_agent │
│  admin             → admin_agent          │
│  teacher           → teacher_agent        │
│  student           → student_agent        │
└────────┬─────────────────────────────────┘
         │
         ▼
    ┌────────┐
    │  Tool  │  ← 41 个工具，按角色 + 意图双重过滤
    │  Node  │
    └───┬────┘
        │ (ReAct 循环，直到 LLM 决定结束)
        ▼
    AI 自然语言回复
```

**核心设计理念：注意力隔离** — 按「角色 × 意图」把 LLM 拆成 6 个专用 Agent，每个 Agent 只看到自己相关的 prompt 和工具白名单，避免工具误用、规则互相干扰和越权。

---

## 🔧 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| AI 框架 | LangGraph 1.2, LangChain 1.3 | ReAct 循环 + StateGraph 编排 |
| LLM | 火山方舟（豆包） | 通过 OpenAI 兼容接口调用 |
| Web | FastAPI 0.109 + Uvicorn | 异步 HTTP 服务（含 SSE 流式） |
| 数据库 | PostgreSQL 16 + pgvector | 业务数据 + 向量存储 |
| ORM | SQLAlchemy 2.0 异步 | AsyncSession + 连接池 |
| 向量 | 阿里云 text-embedding-v4 | OpenAI 兼容 Embedding 接口 |
| 缓存 | Redis | 缓存 + 分布式锁 |
| 日志 | Loguru | 控制台彩色 + JSON 文件 |
| 熔断 | PyBreaker | LLM/API 调用保护 |
| 部署 | Docker Compose | PostgreSQL + pgvector |

---

## 🚀 快速启动

### 1. 克隆 & 环境准备

```bash
git clone <your-repo-url>
cd agent_system

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key 和数据库连接信息
```

`.env` 关键配置：

```env
# LLM（火山方舟，OpenAI 兼容接口）
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
LLM_BASE_DATA_URL=https://ark.cn-beijing.volces.com/api/v3/
LLM_MODEL=ep-xxx-xxx            # 火山方舟推理接入点 ID

# Embedding（阿里云百炼 MaaS，OpenAI 兼容接口）
EMBEDDING_API_KEY=sk-your-key-here
EMBEDDING_BASE_URL=https://ws-xxx.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4

# 数据库
DB_HOST=localhost
DB_PORT=5434
DB_NAME=test_database
DB_USER=postgres
DB_PASSWORD=123456
```

### 3. 启动数据库

```bash
docker compose up -d
```

这会启动 PostgreSQL 16 + pgvector，端口映射到 `5434`。

### 4. 初始化数据 & 知识库索引

```bash
# 建表 + 导入测试数据
python scripts/init_db.py

# 构建 RAG 知识库索引（读取 data/knowledge/*.md → embedding → 写入 PG）
python scripts/build_index.py
```

### 5. 启动服务

```bash
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. 验证

```bash
# 健康检查
curl http://localhost:8000/health

# 对话测试
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "9", "message": "小明今天有课吗？"}'

# 调试面板（可视化）
open http://localhost:8000/api/debug
```

---

## 📡 API 接口

### 对话接口

**`POST /api/chat`**

```json
// 请求
{
  "user_id": "9",
  "message": "小明今天有课吗？",
  "thread_id": "optional-session-id",
  "wx_openid": ""
}

// 响应
{
  "code": 200,
  "message": "success",
  "reply": "小明今天有2节课：\n1. 钢琴课 15:00-16:00\n2. 乐理课 17:00-18:00"
}
```

### 调试面板

**`GET /api/debug`** — 可视化调试面板，可查看：
- 意图分类结果
- 工具调用链
- RAG 召回片段 + 相似度
- 最终回答

### 调试接口

**`POST /api/debug/chat`** — 返回完整 trace 信息的对话接口

---

## 🎯 核心特性

### 1. 六路角色路由（Router 架构）

路由分两级：先按角色（4 种）分发，家长角色再按意图（3 路）细分。

| 角色 | 意图 | 路由到 |
|------|------|--------|
| parent（家长/客服） | `parent_schedule`：有时间锚点（"今天""周三""几点"） | schedule_agent |
| parent（家长/客服） | `parent_course`：问内容（"有什么课""多少钱"） | course_rag_agent |
| parent（家长/客服） | `general`：退费/地址/闲聊/问候 | parent_service_agent |
| admin（教务） | —（非家长角色短路到 general） | admin_agent |
| teacher（教师） | —（非家长角色短路到 general） | teacher_agent |
| student（学生） | —（非家长角色短路到 general） | student_agent |

分类时注入三层上下文：
- **对话历史压缩** — 消除指代歧义（"那明天呢"知道"那"指什么）
- **用户画像注入** — 孩子姓名预加载（避免 LLM 幻觉编造）
- **时间上下文** — 显式告诉 LLM 今天是几月几号星期几

### 2. 双层权限控制

```
permission_check（粗粒度）     AGENT_PERMISSIONS_MATRIX（细粒度）
      │                              │
  能不能用系统？                  能用哪些具体工具？
      │                              │
  user_role 白名单              resource × operation 矩阵
  agent_role 白名单              @tool 装饰器自动校验
```

4 种角色 × 10 个资源域 × 读写分离，每个工具调用都经过权限校验。

### 3. 工具系统（@tool 装饰器）

只需在 Service 方法上加一个装饰器，自动获得：
- ✅ 参数 Schema → LangChain StructuredTool
- ✅ 权限校验 → 对照权限矩阵
- ✅ 统一返回 → ServiceResult 包装
- ✅ 日志记录 → trace_id 全链路追踪
- ✅ 数据脱敏 → 手机号/邮箱自动打码
- ✅ 异常捕获 → 统一错误格式

### 4. RAG 双重查询

```
用户问"钢琴课多少钱"
    │
    ├── rag_search("钢琴课 价格")  → 知识库（课程介绍）
    │
    └── query_courses("钢琴")      → 数据库（结构化价格）
    │
    ▼
综合回答："钢琴课 ¥2000/期，共16课时，由王老师授课..."
```

### 5. 预排课审核流程

```
家长提交预排课 → status=pending
                    │
    ┌───────────────▼────────────────┐
    │ 老师调用 get_pending_reviews() │
    │   查看所有待审核               │
    │       │                        │
    │  ┌────┴────┐                   │
    │  ▼         ▼                   │
    │ approve  reject                │
    │  │         │                   │
    │  ▼         ▼                   │
    │ 自动生成  填写拒绝原因          │
    │ 正式排课  通知家长              │
    └────────────────────────────────┘
```

---

## 📁 项目结构

```
agent_system/
├── agent/                     # Agent 运行时
│   ├── llm.py                 # ChatModel 创建 + bind_tools
│   └── state.py               # AgentState 定义
│
├── core/                      # 核心基础设施
│   ├── context.py             # CTX 全链路上下文
│   ├── database.py            # AsyncDatabase 连接池
│   ├── settings.py            # 全局配置
│   ├── security.py            # 密码哈希 + JWT 签发/校验
│   ├── scheduler.py           # APScheduler 定时任务（消课扫描）
│   ├── dao/                   # DAO 基类
│   │   └── sqlalchemy_base_dao.py
│   ├── graph/                 # LangGraph 工作流
│   │   ├── builder.py         # StateGraph 构建
│   │   ├── nodes/             # 图节点
│   │   │   ├── agent_node.py      # LLM 调用
│   │   │   ├── tool_node.py       # 工具执行
│   │   │   ├── classify_intent.py # 意图分类
│   │   │   ├── permission_check.py# 权限校验
│   │   │   └── prefetch_node.py   # 数据预取
│   │   └── tools/             # 工具桥接
│   │       ├── loader.py      # 工具自动发现
│   │       └── context_binder.py  # CTX 注入
│   ├── prompt_templates/      # 提示词模板
│   └── service/               # Service 基础设施
│       ├── decorators.py      # @tool 装饰器
│       ├── models.py          # ServiceResult + 权限矩阵
│       └── utils.py           # 脱敏 + DAO 获取
│
├── dal/                       # 数据访问层
│   ├── models/                # ORM 表模型（12 张表）
│   ├── dao/                   # 单表 CRUD
│   └── query/                 # 多表关联查询
│
├── service/                   # 业务服务（AI 可调用的工具）
│   ├── user_service.py        # 用户 CRUD
│   ├── course_service.py      # 课程管理
│   ├── schedule_service.py    # 排课管理
│   ├── student_course_service.py  # 选课管理
│   ├── parent_student_service.py  # 家长-学生关联
│   ├── pre_schedule_service.py    # 预排课审核
│   ├── lesson_consumption_service.py # 消课扣课时
│   ├── teacher_todo_service.py    # 教师待办
│   ├── notification_service.py    # 通知
│   ├── conversation_service.py    # 会话/消息持久化
│   └── rag_service.py         # RAG 知识库检索
│
├── schemas/                   # Pydantic 数据模型
├── api/routers/               # HTTP 接口
│   ├── ai_chat_router.py      # 对话 + SSE 流式
│   ├── auth_router.py         # 登录/注册（JWT）
│   └── debug_router.py        # 调试面板
├── infrastructure/            # 向量数据库 + Embedding
├── utils/                     # 日志 + Redis
├── circuit/                   # 熔断器（PyBreaker）
├── scripts/                   # 初始化 + 建索引脚本
├── data/knowledge/            # RAG 知识库源文件
├── test/                      # 测试
├── docs/                      # 设计文档
├── main.py                    # 入口
├── compose.yml                # Docker Compose
└── requirements.txt           # 依赖
```

---

## 🧪 测试

```bash
# 运行全部测试
pytest

# 按模块运行
pytest test/dao/           # DAO 测试
pytest test/service/       # Service 集成测试
pytest test/dal/query/     # QueryService 测试
pytest test/rag/           # RAG 测试
pytest test/graph/         # Graph 集成测试
```

---

## 📝 开发指南

### 新增一个 AI 工具

1. 在 `service/` 对应 Service 类中添加方法
2. 加上 `@tool(ToolMeta(...))` 装饰器
3. 在 `core/service/models.py` 权限矩阵中注册
4. 工具自动被发现，无需修改其他文件

详见 [开发文档](开发文档.text)

---

## 📋 路线图

- [x] LangGraph ReAct 循环
- [x] Router 六路角色路由
- [x] 双层权限控制
- [x] RAG 知识库检索（pgvector）
- [x] 预排课审核流程
- [x] 可视化调试面板
- [x] SSE 流式输出（/chat_stream）
- [ ] Redis 对话记忆持久化（当前记忆存 PostgreSQL）
- [x] API 鉴权（JWT）
- [ ] 多模态支持（图片理解）
- [ ] 可观测性（LangFuse tracing）
- [ ] CI/CD Pipeline

---

## 📄 License

MIT
