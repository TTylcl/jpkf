数据库设计依据	定义所有表结构、字段说明、索引设计、表关系


1	user_info	    用户信息	   没有用户，系统给谁用？
2	session_info	会话管理	AI客服的核心，没它对话无法追踪
3	chat_message	消息记录	存对话内容，否则AI答完就丢了
4	course_info	    课程信息	    教务系统的核心数据
5	pre_schedule	预排课表	核心业务流程（学生提交→老师审核）

以下是对该数据库设计的详细依据分析，涵盖表结构定义、字段说明、索引设计及表关系四个维度：
一、表结构定义依据
该设计围绕 **“AI 教育咨询 + 课程排课”** 的核心业务场景展开，通过 5 张表实现用户管理、会话交互、课程运营、排课流程的完整闭环。
表格
表名	设计依据（业务场景 + 技术原则）
user_info	业务：系统核心主体，需区分学生、老师、管理员、访客等角色；技术：使用枚举（ENUM）约束角色类型，避免非法值；触发器自动维护时间戳，保证审计字段准确性。
session_info	业务：连接用户与服务的桥梁，需支持 AI / 人工 / 转接等多服务类型，并追踪会话生命周期；技术：状态机（status）管理会话流转，外键关联用户保证数据归属清晰。
chat_message	业务：记录交互细节，需区分消息发送方（用户 / AI / 人工）、类型（文本 / 图片等），并追溯 AI 回答的知识来源；技术：通过reference_kb_id和intent支持 AI 系统的可解释性与优化。
course_info	业务：教育产品核心载体，需支持直播 / 录播 / 混合等多类型课程，并管理上下架状态；技术：冗余teacher_name字段（读多写少场景），减少高频查询的 JOIN 开销。
pre_schedule	业务：学生约课流程的核心，需支持 “提交 - 审核 - 排课” 的状态流转；技术：审核状态枚举（pending/approved/rejected）明确业务节点，外键关联学生与课程保证数据一致性。
二、字段说明依据
字段设计严格遵循 **“业务含义明确 + 数据完整性约束 + 扩展性预留”** 的原则：
1. 通用字段设计
*_id（如user_id、session_id）：使用BIGSERIAL自增主键，保证分布式场景下的唯一性与高性能。
created_at/updated_at：标准审计字段，updated_at通过触发器自动更新，无需应用层干预，保证数据时效性。
status：通用状态控制（如用户禁用 / 启用、课程上架 / 下架），使用SMALLINT或ENUM，兼顾可读性与存储效率。
2. 业务字段设计
枚举类型（user_type_enum、session_type_enum等）：
替代VARCHAR，限制字段取值范围，避免脏数据（如用户类型不会出现“studet”拼写错误）。
比字符串更节省存储空间，查询性能更高。
冗余字段（如teacher_name）：
针对 “查询课程列表时需展示老师姓名” 的高频场景，避免每次JOIN user_info表，优化读性能（以空间换时间）。
AI 专属字段（reference_kb_id、intent）：
reference_kb_id：追溯 AI 回答引用的知识库，支持可解释性与知识纠错。
intent：记录用户意图识别结果，用于后续对话分析与模型优化。
三、索引设计依据
索引设计聚焦 **“高频查询场景 + 外键关联性能 + 排序 / 过滤效率”**，避免过度索引（增加写入开销）：
表格
索引名	设计依据（对应查询场景）
idx_user_info_user_type	按角色查询用户（如 “查询所有老师”）。
idx_user_info_status	按状态筛选用户（如 “查询禁用账号”）。
idx_session_info_user_id	核心查询：查询某用户的历史会话列表（高频场景，如用户中心 “我的会话”）。
idx_session_info_status	筛选活跃 / 已关闭会话（如客服工作台 “待处理会话”）。
idx_session_info_start_time	按时间范围统计会话（如 “查看昨日 AI 服务会话量”）。
idx_chat_message_session_id	核心查询：获取某会话的所有消息（聊天窗口加载历史消息，需按created_at排序）。
idx_course_info_teacher_id	查询某老师的授课列表（如老师中心 “我的课程”）。
idx_pre_schedule_student_id	查询某学生的预排课申请（如学生端 “我的约课记录”）。
idx_pre_schedule_status	筛选待审核 / 已通过的预排课（如教务工作台 “待处理申请”）。
设计原则：
外键字段（如session_info.user_id）默认建索引，加速JOIN操作。
复合查询场景可考虑联合索引（如(session_id, created_at)），但当前设计已覆盖核心场景。

关系说明与依据
user_info ↔ session_info（1:N）
关系：一个用户可发起多个会话，一个会话属于一个用户。
依据：通过session_info.user_id外键关联user_info.user_id，保证会话必须归属有效用户，避免 “孤儿会话”。
session_info ↔ chat_message（1:N）
关系：一个会话包含多条消息，一条消息属于一个会话。
依据：通过chat_message.session_id外键关联，保证消息与会话的绑定关系，支持聊天记录的完整追溯。
user_info ↔ course_info（1:N）
关系：一个老师可教授多门课程，一门课程归属一个老师。
依据：course_info.teacher_id外键关联user_info.user_id，同时冗余teacher_name优化查询。
user_info ↔ pre_schedule（1:N）
关系：学生提交预排课申请，管理员 / 老师审核。
依据：pre_schedule.student_id关联学生，reviewer_id（隐含，需补充）关联审核人，明确流程角色。
course_info ↔ pre_schedule（1:N）
关系：预排课申请需关联具体课程。
依据：pre_schedule.course_id外键关联，保证申请的课程真实存在，避免无效约课。
五、整体设计亮点总结
业务与技术的平衡：既通过枚举、外键保证数据完整性，又通过冗余字段、索引优化性能。
AI 场景的针对性：reference_kb_id、intent等字段支持 AI 系统的可解释性与迭代优化。
扩展性预留：枚举类型（如user_type_enum）可轻松新增角色，JSON 字段（当前未使用）可预留扩展属性。
审计与可追溯：created_at/updated_at、reviewer_id等字段支持操作审计与问题回溯。