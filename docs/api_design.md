接口设计依据	定义所有接口路径、参数、响应体、错误码

---

# 教务客服AI系统 API 接口文档

## 基础信息

- **Base URL**: `https://api.example.com`
- **版本**: v1.0.0
- **协议**: HTTPS
- **认证方式**: Bearer Token (JWT)

---

## 通用约定

### 请求头

```http
Content-Type: application/json
Authorization: Bearer <token>
X-Request-ID: <uuid>  # 可选，用于链路追踪
```

### 响应格式

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": 1714060800000
}
```

**失败响应**

```json
{
  "code": 40001,
  "message": "参数错误：用户名不能为空",
  "data": null,
  "timestamp": 1714060800000
}
```

### 通用错误码

| 错误码 | 说明 |
|-------|------|
| 200 | 成功 |
| 40001 | 参数错误 |
| 40002 | 数据格式错误 |
| 40101 | 未登录或Token过期 |
| 40102 | 权限不足 |
| 40103 | 账号已被禁用 |
| 40401 | 资源不存在 |
| 40901 | 资源冲突 |
| 50001 | 服务器内部错误 |
| 50002 | 数据库错误 |
| 50003 | 第三方服务异常 |

---

## 1. 认证模块

### 1.1 用户登录

```
POST /api/auth/login
```

**权限要求**: 无（公开接口）

**请求参数**

```json
{
  "username": "string",    // 必填，用户名或手机号
  "password": "string",    // 必填，密码
  "login_type": "string"   // 可选，登录类型：password/sms/wework，默认password
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user_info": {
      "user_id": "U001",
      "username": "parent001",
      "real_name": "张三",
      "role": "parent",
      "phone": "138****1234",
      "avatar": "https://cdn.example.com/avatar/001.jpg"
    }
  }
}
```

**失败响应**

```json
// 用户名或密码错误
{ "code": 40101, "message": "用户名或密码错误", "data": null }

// 账号已被禁用
{ "code": 40103, "message": "账号已被禁用，请联系管理员", "data": null }

// 参数错误
{ "code": 40001, "message": "参数错误：用户名不能为空", "data": null }
```

---

### 1.2 企业微信登录

```
POST /api/auth/wework-login
```

**权限要求**: 无（公开接口）

**请求参数**

```json
{
  "code": "string",     // 必填，企业微信授权码
  "corp_id": "string"   // 必填，企业ID
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user_info": {
      "user_id": "P001",
      "username": "parent001",
      "real_name": "张三",
      "role": "parent",
      "phone": "138****1234",
      "wework_id": "zhangsan_wework",
      "is_bound": true
    }
  }
}
```

**失败响应**

```json
// 企业微信授权失败
{ "code": 50003, "message": "企业微信授权失败：无效的授权码", "data": null }

// 用户未注册
{ "code": 40401, "message": "用户未注册，请联系管理员", "data": null }
```

---

### 1.3 刷新Token

```
POST /api/auth/refresh-token
```

**权限要求**: 已登录

**请求参数**

```json
{
  "refresh_token": "string"
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 7200
  }
}
```

---

### 1.4 登出

```
POST /api/auth/logout
```

**权限要求**: 已登录

**成功响应**

```json
{ "code": 200, "message": "登出成功", "data": null }
```

---

## 2. 家长绑定模块

### 2.1 绑定学生

```
POST /api/parent/bind-student
```

**权限要求**: role = parent

**请求参数**

```json
{
  "student_name": "string",      // 必填，学生姓名
  "student_phone": "string",     // 必填，学生手机号后4位
  "verification_code": "string", // 必填，验证码（学校提供）
  "relationship": "string"       // 必填，关系：father/mother/other
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "绑定成功",
  "data": {
    "binding_id": "B001",
    "student_id": "S001",
    "student_name": "小明",
    "relationship": "father",
    "bound_at": "2026-04-25T10:00:00+08:00"
  }
}
```

**失败响应**

```json
// 学生不存在
{ "code": 40401, "message": "未找到该学生，请检查姓名和手机号", "data": null }

// 验证码错误
{ "code": 40102, "message": "验证码错误", "data": null }

// 已绑定
{ "code": 40901, "message": "您已绑定该学生，请勿重复绑定", "data": null }
```

---

### 2.2 解绑学生

```
DELETE /api/parent/unbind-student/{student_id}
```

**权限要求**: role = parent

**成功响应**

```json
{ "code": 200, "message": "解绑成功", "data": null }
```

---

### 2.3 查询绑定学生列表

```
GET /api/parent/bindings
```

**权限要求**: role = parent

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 2,
    "bindings": [
      {
        "binding_id": "B001",
        "student_id": "S001",
        "student_name": "小明",
        "student_phone": "138****1234",
        "relationship": "父亲",
        "is_primary": true,
        "bound_at": "2026-01-15T10:00:00+08:00"
      }
    ]
  }
}
```

---

## 3. 学生/家长业务模块

### 3.1 查询我的课程表

```
GET /api/student/courses
```

**权限要求**: role = student 或 parent

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| student_id | string | 否 | 学生ID（家长查询时必填） |
| start_date | string | 否 | 开始日期 YYYY-MM-DD，默认今天 |
| end_date | string | 否 | 结束日期 YYYY-MM-DD，默认7天后 |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "student_id": "S001",
    "student_name": "小明",
    "date_range": {
      "start_date": "2026-04-25",
      "end_date": "2026-05-02"
    },
    "courses": [
      {
        "schedule_id": "CS001",
        "course_name": "数学",
        "teacher_name": "李老师",
        "classroom": "A101",
        "date": "2026-04-28",
        "start_time": "14:00",
        "end_time": "16:00",
        "status": "scheduled"
      }
    ]
  }
}
```

**失败响应**

```json
// 家长未绑定该学生
{ "code": 40102, "message": "您未绑定该学生，无权查询", "data": null }

// 参数错误
{ "code": 40001, "message": "参数错误：日期格式不正确", "data": null }
```

---

### 3.2 提交预排课申请

```
POST /api/student/pre-schedule
```

**权限要求**: role = student 或 parent

**请求参数**

```json
{
  "student_id": "string",      // 可选，学生ID（家长提交时必填）
  "course_id": "string",       // 必填，课程ID
  "preferred_times": [         // 必填，期望时间段（最多3个）
    {
      "weekday": 1,            // 星期几：1-7
      "start_time": "14:00",
      "end_time": "16:00",
      "priority": 1            // 优先级：1最高
    }
  ],
  "remark": "string"           // 可选，备注说明
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "提交成功，请等待老师审核",
  "data": {
    "pre_schedule_id": "PS001",
    "student_id": "S001",
    "course_name": "数学",
    "preferred_times": [...],
    "status": "pending",
    "created_at": "2026-04-25T10:00:00+08:00"
  }
}
```

**失败响应**

```json
// 存在未处理的申请
{
  "code": 40901,
  "message": "您已有待审核的预排课申请，请等待审核后再提交",
  "data": { "existing_id": "PS000", "status": "pending" }
}
```

---

### 3.3 查询我的预排课申请

```
GET /api/student/pre-schedules
```

**权限要求**: role = student 或 parent

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| student_id | string | 否 | 学生ID（家长查询时必填） |
| status | string | 否 | 状态筛选：pending/approved/rejected/cancelled |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 3,
    "items": [
      {
        "pre_schedule_id": "PS001",
        "course_name": "数学",
        "preferred_times": [...],
        "status": "pending",
        "created_at": "2026-04-25T10:00:00+08:00"
      },
      {
        "pre_schedule_id": "PS002",
        "course_name": "英语",
        "status": "approved",
        "reviewer_name": "李老师",
        "review_comment": "已安排",
        "confirmed_schedule": {
          "schedule_id": "CS010",
          "date": "2026-05-05",
          "start_time": "14:00",
          "end_time": "16:00"
        },
        "created_at": "2026-04-20T09:00:00+08:00",
        "reviewed_at": "2026-04-21T15:00:00+08:00"
      }
    ]
  }
}
```

---

### 3.4 取消预排课申请

```
POST /api/student/pre-schedule/{pre_schedule_id}/cancel
```

**权限要求**: role = student 或 parent

**请求参数**

```json
{
  "reason": "string"  // 可选，取消原因
}
```

**成功响应**

```json
{ "code": 200, "message": "取消成功", "data": null }
```

**失败响应**

```json
// 状态不允许取消
{
  "code": 40002,
  "message": "该申请已审核，无法取消",
  "data": { "current_status": "approved" }
}
```

---

### 3.5 提交请假申请

```
POST /api/student/leave-application
```

**权限要求**: role = student 或 parent

**请求参数**

```json
{
  "student_id": "string",       // 可选，学生ID（家长提交时必填）
  "leave_type": "string",       // 必填，请假类型：sick/personal/other
  "start_date": "string",       // 必填，开始日期 YYYY-MM-DD
  "end_date": "string",         // 必填，结束日期 YYYY-MM-DD
  "reason": "string",           // 必填，请假原因
  "attachment_url": "string"    // 可选，附件URL（病假需提供病假条）
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "提交成功，请等待老师审核",
  "data": {
    "leave_id": "LA001",
    "student_name": "小明",
    "leave_type": "sick",
    "date_range": {
      "start_date": "2026-04-28",
      "end_date": "2026-04-29"
    },
    "status": "pending",
    "created_at": "2026-04-25T10:00:00+08:00"
  }
}
```

**失败响应**

```json
// 日期冲突
{
  "code": 40901,
  "message": "该时间段已有待审核的请假申请",
  "data": { "existing_leave_id": "LA000" }
}
```

---

### 3.6 查询我的请假记录

```
GET /api/student/leave-applications
```

**权限要求**: role = student 或 parent

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| student_id | string | 否 | 学生ID（家长查询时必填） |
| status | string | 否 | 状态筛选 |
| start_date | string | 否 | 查询开始日期 |
| end_date | string | 否 | 查询结束日期 |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 5,
    "items": [
      {
        "leave_id": "LA001",
        "leave_type": "sick",
        "start_date": "2026-04-28",
        "end_date": "2026-04-29",
        "days": 2,
        "reason": "感冒发烧",
        "status": "approved",
        "reviewer_name": "李老师",
        "review_comment": "同意，注意休息",
        "created_at": "2026-04-25T10:00:00+08:00",
        "reviewed_at": "2026-04-25T14:00:00+08:00"
      }
    ]
  }
}
```

---

### 3.7 撤销请假申请

```
POST /api/student/leave-application/{leave_id}/cancel
```

**权限要求**: role = student 或 parent

**成功响应**

```json
{ "code": 200, "message": "撤销成功", "data": null }
```

**失败响应**

```json
{
  "code": 40002,
  "message": "该请假已生效或已审核，无法撤销",
  "data": { "current_status": "approved" }
}
```

---

## 4. 老师业务模块

### 4.1 查询待审核预排课

```
GET /api/teacher/pending-pre-schedules
```

**权限要求**: role = teacher

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 15,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "pre_schedule_id": "PS001",
        "student_id": "S001",
        "student_name": "小明",
        "student_phone": "138****1234",
        "course_name": "数学",
        "preferred_times": [
          { "weekday": 1, "start_time": "14:00", "end_time": "16:00", "priority": 1 }
        ],
        "remark": "希望安排在周一下午",
        "status": "pending",
        "created_at": "2026-04-25T10:00:00+08:00"
      }
    ]
  }
}
```

---

### 4.2 审核预排课申请

```
POST /api/teacher/review-pre-schedule/{pre_schedule_id}
```

**权限要求**: role = teacher

**请求参数**

```json
{
  "action": "string",          // 必填，approve/reject
  "schedule_info": {           // action=approve时必填
    "date": "string",          // 排课日期 YYYY-MM-DD
    "start_time": "string",    // 开始时间 HH:mm
    "end_time": "string",      // 结束时间 HH:mm
    "classroom": "string",     // 教室
    "teacher_id": "string"     // 授课老师ID
  },
  "comment": "string"          // 可选，审核意见
}
```

**成功响应（通过）**

```json
{
  "code": 200,
  "message": "审核通过，已生成正式排课",
  "data": {
    "pre_schedule_id": "PS001",
    "status": "approved",
    "confirmed_schedule": {
      "schedule_id": "CS010",
      "course_name": "数学",
      "student_name": "小明",
      "teacher_name": "李老师",
      "date": "2026-05-05",
      "start_time": "14:00",
      "end_time": "16:00",
      "classroom": "A101"
    },
    "reviewed_at": "2026-04-25T15:00:00+08:00"
  }
}
```

**失败响应**

```json
// 时间冲突
{
  "code": 40901,
  "message": "该时间段已有其他排课",
  "data": {
    "conflict_schedule": {
      "schedule_id": "CS008",
      "course_name": "英语",
      "date": "2026-05-05",
      "time_range": "14:00-16:00"
    }
  }
}
```

---

### 4.3 查询待审核请假

```
GET /api/teacher/pending-leaves
```

**权限要求**: role = teacher

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 8,
    "items": [
      {
        "leave_id": "LA001",
        "student_name": "小明",
        "leave_type": "sick",
        "start_date": "2026-04-28",
        "end_date": "2026-04-29",
        "days": 2,
        "reason": "感冒发烧",
        "attachment_url": "https://cdn.example.com/leave/001.jpg",
        "status": "pending"
      }
    ]
  }
}
```

---

### 4.4 审核请假申请

```
POST /api/teacher/review-leave/{leave_id}
```

**权限要求**: role = teacher

**请求参数**

```json
{
  "action": "string",    // 必填，approve/reject
  "comment": "string"    // 可选，审核意见
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "审核完成",
  "data": {
    "leave_id": "LA001",
    "status": "approved",
    "reviewer_name": "李老师",
    "review_comment": "同意，注意休息",
    "reviewed_at": "2026-04-25T15:00:00+08:00"
  }
}
```

---

### 4.5 查询我的学生列表

```
GET /api/teacher/my-students
```

**权限要求**: role = teacher

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| keyword | string | 否 | 搜索关键词 |
| status | string | 否 | 学生状态 |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 45,
    "items": [
      {
        "student_id": "S001",
        "real_name": "小明",
        "phone": "138****1234",
        "status": "active",
        "courses": ["数学", "物理"],
        "next_class": {
          "date": "2026-04-28",
          "time": "14:00-16:00",
          "course": "数学"
        }
      }
    ]
  }
}
```

---

### 4.6 查询排课日历

```
GET /api/teacher/schedule-calendar
```

**权限要求**: role = teacher

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| start_date | string | 是 | 开始日期 YYYY-MM-DD |
| end_date | string | 是 | 结束日期 YYYY-MM-DD |
| student_id | string | 否 | 学生ID筛选 |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "teacher_name": "李老师",
    "date_range": { "start_date": "2026-04-25", "end_date": "2026-05-02" },
    "schedules": [
      {
        "schedule_id": "CS001",
        "date": "2026-04-28",
        "weekday": 1,
        "start_time": "14:00",
        "end_time": "16:00",
        "course_name": "数学",
        "student_name": "小明",
        "classroom": "A101",
        "status": "scheduled"
      }
    ]
  }
}
```

---

## 5. 管理员模块

### 5.1 用户管理 - 查询用户列表

```
GET /api/admin/users
```

**权限要求**: role = admin

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| keyword | string | 否 | 搜索关键词 |
| role | string | 否 | 角色筛选 |
| status | string | 否 | 状态筛选 |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 120,
    "items": [
      {
        "user_id": "U001",
        "username": "parent001",
        "real_name": "张三",
        "role": "parent",
        "phone": "13812345678",
        "status": "active",
        "created_at": "2026-01-15T10:00:00+08:00",
        "last_login_at": "2026-04-25T09:00:00+08:00"
      }
    ]
  }
}
```

---

### 5.2 用户管理 - 创建用户

```
POST /api/admin/users
```

**权限要求**: role = admin

**请求参数**

```json
{
  "username": "string",
  "password": "string",
  "real_name": "string",
  "role": "string",          // student/teacher/parent/admin
  "phone": "string",
  "email": "string",
  "avatar_url": "string"
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "创建成功",
  "data": {
    "user_id": "U100",
    "username": "newuser",
    "real_name": "新用户",
    "role": "student",
    "status": "active"
  }
}
```

---

### 5.3 用户管理 - 更新用户

```
PUT /api/admin/users/{user_id}
```

**权限要求**: role = admin

**请求参数**

```json
{
  "real_name": "string",
  "phone": "string",
  "email": "string",
  "status": "string",
  "avatar_url": "string"
}
```

---

### 5.4 课程管理 - 查询课程列表

```
GET /api/admin/courses
```

**权限要求**: role = admin

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 20,
    "items": [
      {
        "course_id": "C001",
        "course_name": "数学",
        "teacher_name": "李老师",
        "total_hours": 40,
        "completed_hours": 15,
        "status": "active",
        "students_count": 5
      }
    ]
  }
}
```

---

### 5.5 系统统计 - 仪表盘数据

```
GET /api/admin/dashboard
```

**权限要求**: role = admin

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "statistics": {
      "total_students": 120,
      "total_teachers": 15,
      "total_parents": 95,
      "active_courses": 45,
      "today_classes": 12,
      "pending_approvals": 8
    },
    "recent_activities": [
      {
        "type": "leave_approved",
        "content": "李老师批准了小明的请假申请",
        "created_at": "2026-04-25T15:00:00+08:00"
      }
    ],
    "alerts": [
      { "type": "warning", "message": "有3个预排课申请超过3天未审核" }
    ]
  }
}
```

---

## 6. 企业微信机器人接口

### 6.1 接收企业微信回调

```
POST /api/wework/callback
```

**权限要求**: 验证签名

**请求参数**

```json
{
  "MsgType": "text",
  "Content": "@机器人 查一下小明下周课表",
  "FromUserName": "zhangsan",
  "CreateTime": 1714060800,
  "ChatId": "wrXXXXXXXXXX"
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "reply_type": "text",
    "content": "小明下周课表：\n周一 14:00-16:00 数学\n周三 10:00-12:00 英语"
  }
}
```

---

### 6.2 发送消息到企业微信群

```
POST /api/wework/send-message
```

**权限要求**: 内部调用

**请求参数**

```json
{
  "chat_id": "string",
  "msg_type": "string",      // text/markdown/card
  "content": "string",
  "card_data": {
    "title": "string",
    "description": "string",
    "url": "string"
  }
}
```

---

## 7. 健康检查接口

```
GET /api/health
```

**权限要求**: 无

**成功响应**

```json
{
  "code": 200,
  "message": "healthy",
  "data": {
    "service": "education-customer-service",
    "version": "1.0.0",
    "database": "connected",
    "redis": "connected"
  }
}
```

---

## 附录

### A. 权限矩阵

| 接口模块 | student | parent | teacher | admin |
|---------|---------|--------|---------|-------|
| 查询自己课程 | ✅ | ✅ | ✅ | ✅ |
| 查询他人课程 | ❌ | ✅(绑定学生) | ✅ | ✅ |
| 提交预排课 | ✅ | ✅(绑定学生) | ❌ | ❌ |
| 审核预排课 | ❌ | ❌ | ✅ | ✅ |
| 提交请假 | ✅ | ✅(绑定学生) | ❌ | ❌ |
| 审核请假 | ❌ | ❌ | ✅ | ✅ |
| 用户管理 | ❌ | ❌ | ❌ | ✅ |
| 系统统计 | ❌ | ❌ | ❌ | ✅ |

---

### B. 状态码速查

**预排课状态**

| 状态 | 说明 | 允许操作 |
|------|------|---------|
| pending | 待审核 | 学生可取消 |
| approved | 已通过 | 不可操作 |
| rejected | 已拒绝 | 可重新提交 |
| cancelled | 已取消 | 可重新提交 |
| confirmed | 已生成正式排课 | 不可操作 |

**请假状态**

| 状态 | 说明 | 允许操作 |
|------|------|---------|
| pending | 待审核 | 学生可撤销 |
| approved | 已通过 | 等待生效 |
| rejected | 已拒绝 | 可重新提交 |
| cancelled | 已撤销 | 可重新提交 |
| effective | 已生效 | 不可操作 |

---

### C. 日期时间格式

| 字段类型 | 格式 | 示例 |
|---------|------|------|
| 日期 | YYYY-MM-DD | 2026-04-25 |
| 时间 | HH:mm | 14:00 |
| 日期时间 | ISO 8601 | 2026-04-25T14:00:00+08:00 |
| 时间戳 | Unix Timestamp (ms) | 1714060800000 |

---

完整API文档已展示！需要我继续补充其他内容吗？