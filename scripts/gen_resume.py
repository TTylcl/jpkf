# -*- coding: utf-8 -*-
"""
功能：生成个人简历 v3（两栏设计 + 成果导向）
说明：
  - 融合「参考模板(1.docx)的版式感」与「AI 应用岗的卖点前置」
  - 布局：顶部深蓝横幅（姓名/意向/钩子） + 两栏主体
      左栏（浅底）：头像占位 / 基本信息 / 技能证书
      右栏（白底）：项目经历（前置）→ 工作经历 → 教育背景 → 自我评价
  - 成果导向：项目用「问题 → 方案 → 规模证据」讲
输出：桌面 简历_AI应用开发_定稿.docx
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DOC_PATH = r"C:/Users/97487/Desktop/简历_宁荣泽_AI应用开发.docx"

FONT = "微软雅黑"
DARK = RGBColor(0x22, 0x3A, 0x5E)      # 深蓝（横幅 / 标题）
ACCENT = RGBColor(0x2E, 0x6F, 0xB5)    # 强调蓝
GRAY = RGBColor(0x60, 0x60, 0x60)      # 次要灰
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT_WHITE = RGBColor(0xD8, 0xE2, 0xEF)  # 横幅上的浅字

SIDEBAR_FILL = "EDF2F8"   # 左栏浅底
BANNER_FILL = "223A5E"    # 顶部横幅深蓝


# ─────────────────────────── 底层工具 ───────────────────────────

def set_font(run, size=10.5, bold=False, color=None, name=FONT):
    """设置 run 的字体 / 字号 / 加粗 / 颜色（含中文字体 eastAsia）"""
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)


def set_cell_shading(cell, fill_hex):
    """给单元格加底色"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def set_cell_margins(cell, top=100, start=140, bottom=100, end=140):
    """设置单元格内边距（单位 dxa，1cm≈567 dxa）"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = OxmlElement(f"w:{tag}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def remove_table_borders(table):
    """去掉表格所有边框（让两栏看起来是色块而非表格）"""
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        borders.append(el)
    tblPr.append(borders)


def fix_table_widths(table, widths_cm):
    """固定表格列宽（python-docx 默认 autofit，需手动锁死）"""
    table.autofit = False
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    for idx, w in enumerate(widths_cm):
        table.columns[idx].width = Cm(w)
        for cell in table.columns[idx].cells:
            cell.width = Cm(w)


def add_para(container, text="", size=10.5, bold=False, color=None,
             align=None, space_before=0, space_after=2, indent=0.0):
    """在 doc 或 cell 里加一个段落，返回 paragraph"""
    p = container.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    if align is not None:
        p.alignment = align
    if text:
        run = p.add_run(text)
        set_font(run, size=size, bold=bold, color=color)
    return p


def add_heading(container, text, color=DARK, size=12, space_before=8, space_after=4):
    """带底线的标题（用于右栏 section）"""
    p = container.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    set_font(run, size=size, bold=True, color=color)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), "2E6FB5")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def add_sidebar_title(cell, text):
    """左栏小标题（白字放深蓝小色条上，更醒目）"""
    p = cell.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    set_font(run, size=11, bold=True, color=WHITE)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "2E6FB5")
    pPr.append(shd)
    # 小色条左右留白
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:left"), "60")
    ind.set(qn("w:right"), "60")
    return p


def add_bullet(container, lead, body, size=10.5, space_after=3):
    """右栏项目条目：lead（问题，加粗）+ body（方案/结果）"""
    p = container.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.left_indent = Cm(0.3)
    r1 = p.add_run(lead)
    set_font(r1, size=size, bold=True)
    r2 = p.add_run(body)
    set_font(r2, size=size)
    return p


# ─────────────────────────── 构建文档 ───────────────────────────

doc = Document()
for section in doc.sections:
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)
    section.left_margin = Cm(1.2)
    section.right_margin = Cm(1.2)

# ══════════ 顶部横幅 ══════════
banner = doc.add_table(rows=1, cols=1)
remove_table_borders(banner)
fix_table_widths(banner, [18.6])
banner_cell = banner.cell(0, 0)
set_cell_shading(banner_cell, BANNER_FILL)
set_cell_margins(banner_cell, top=220, start=200, bottom=220, end=200)

add_para(banner_cell, "宁荣泽", size=24, bold=True, color=WHITE,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
add_para(banner_cell, "求职意向：AI 应用开发 / 大模型应用工程师", size=12, bold=True,
         color=WHITE, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
add_para(banner_cell, "计算机科班 · 独立从 0 搭建可运行的多角色 AI Agent 系统，完整开源、可验证",
         size=10, bold=False, color=SOFT_WHITE, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)

# ══════════ 主体两栏 ══════════
body = doc.add_table(rows=1, cols=2)
remove_table_borders(body)
fix_table_widths(body, [5.0, 13.6])

left = body.cell(0, 0)
right = body.cell(0, 1)
left.vertical_alignment = WD_ALIGN_VERTICAL.TOP
right.vertical_alignment = WD_ALIGN_VERTICAL.TOP
set_cell_shading(left, SIDEBAR_FILL)
set_cell_margins(left, top=120, start=140, bottom=120, end=140)
set_cell_margins(right, top=120, start=200, bottom=120, end=200)

# ── 左栏 ──
add_para(left, "【照片】", size=9, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)

add_sidebar_title(left, "联系方式")
contact = [
    ("电话", "18977560613"),
    ("邮箱", "18977560613@163.com"),
]
for label, value in contact:
    p = add_para(left, space_after=2)
    r1 = p.add_run(label + "　")
    set_font(r1, size=9.5, bold=True, color=DARK)
    r2 = p.add_run(value)
    set_font(r2, size=9.5)

p = add_para(left, space_after=2)
r1 = p.add_run("GitHub　")
set_font(r1, size=9.5, bold=True, color=DARK)
r2 = p.add_run("github.com/TTylcl/jpkf")
set_font(r2, size=8.5, color=ACCENT)

add_sidebar_title(left, "基本信息")
fields = [
    ("出生年月", "1997.03"),
    ("学历", "本科"),
    ("毕业院校", "枣庄学院"),
]
for label, value in fields:
    p = add_para(left, space_after=2)
    r1 = p.add_run(label + "　")
    set_font(r1, size=9.5, bold=True, color=DARK)
    r2 = p.add_run(value)
    set_font(r2, size=9.5)

add_sidebar_title(left, "技能证书")
for line in ["普通话二级乙等", "全国计算机二级", "熟练 Office / WPS"]:
    add_para(left, "· " + line, size=9.5, space_after=2)

# ── 右栏 ──

# 项目经历（前置，主角）
add_heading(right, "项目经历")

p = add_para(right, space_after=2)
r1 = p.add_run("AI 教务客服系统（多角色 Agent）　|　个人开源项目　|　")
set_font(r1, size=11, bold=True)
r2 = p.add_run("Python / FastAPI / LangGraph / PostgreSQL + pgvector")
set_font(r2, size=9.5, color=GRAY)

add_para(right, "项目背景：面向教培机构教务场景的智能客服系统，解决教务咨询、课时管理、家长通知等业务痛点，完整实现多角色 Agent、RAG 检索、业务闭环、安全加固。",
         size=10.5, space_after=3)

add_para(right, "核心职责：全栈独立从零开发，负责架构设计、Agent 编排、后端接口开发、数据库建模、安全漏洞修复、业务流程实现。",
         size=10.5, space_after=3)

add_para(right, "核心实现 & 解决问题：", size=10.5, bold=True, space_before=2, space_after=3)
add_para(right, "核心链路：入口 → JWT 鉴权 → 意图识别 → 六路 Agent 路由（ReAct：41 工具 · 读写 PG + pgvector）→ 存储对话 → 返回结果",
         size=9.5, color=ACCENT, bold=True, space_after=3)
add_bullet(right, "注意力隔离 —— ", "单 Agent 大 prompt 在多工具场景会「工具误用 + 规则互相干扰」，改用 LangGraph Router 按「角色 × 意图」拆成 6 个 Agent，各自独立 prompt + 工具白名单，越权和误用从架构上被隔离，而不是靠 prompt 提醒。")
add_bullet(right, "安全加固 —— ", "补上 JWT 登录鉴权、IDOR 归属校验（工具 owner 标记）、CORS 白名单、LLM 熔断降级，并修掉 debug 接口「靠请求体冒充身份」的越权漏洞。")
add_bullet(right, "RAG 检索 —— ", "pgvector 向量检索 + 意图分类时注入对话历史 / 用户画像 / 时间上下文，解决「那明天呢」这类多轮指代歧义。")
add_bullet(right, "消课闭环 —— ", "APScheduler 定时扫描 → 教师待办 → 消课扣课时 → 通知家长，多步写库业务闭环。")

add_para(right, "项目产出：约 110 源文件 · 6 个 Agent · 41 个自定义工具 · 12 张 ORM 表 · 完整权限矩阵，项目开源、可一键部署运行。",
         size=10.5, bold=True, space_before=2, space_after=6)

# 专业技能
add_heading(right, "专业技能")
add_bullet(right, "大模型应用开发　", "LangGraph、ReAct Agent、RAG、意图识别、Prompt 工程、多 Agent 路由、LLM 熔断降级；具备 Agent 工具开发与权限隔离架构实践。")
add_bullet(right, "后端开发　", "Python、FastAPI、JWT 鉴权、接口安全优化、APScheduler 定时任务。")
add_bullet(right, "数据库 & 向量库　", "PostgreSQL、pgvector、ORM、多表业务设计、权限矩阵设计。")
add_bullet(right, "工具　", "Git、接口调试、漏洞排查；熟悉业务需求拆解与方案文档撰写。", space_after=6)

# 工作经历
add_heading(right, "工作经历")

p = add_para(right, space_after=2)
r1 = p.add_run("娅当　|　机器人部门负责人　")
set_font(r1, size=11, bold=True)
r2 = p.add_run("2024.01 - 2026.07")
set_font(r2, size=9.5, color=GRAY)
add_bullet(right, "课程体系与授课 —— ", "作为部门负责人，从 0 搭建编程、无人机两套课程体系，独立负责课程内容设计与课件开发，并承担一线授课。")
add_bullet(right, "需求拆解与建模 —— ", "把教学业务拆解为模块化课程与角色、权限体系，锻炼复杂业务建模与抽象能力。")
add_bullet(right, "项目落地与协同 —— ", "主导家校沟通与校企合作，对接学校、企业等多方干系人，推动项目从 0 到 1 落地，具备需求分析、方案输出与推进能力。", space_after=6)

p = add_para(right, space_after=2)
r1 = p.add_run("盛通知行　|　编程讲师　")
set_font(r1, size=11, bold=True)
r2 = p.add_run("2019.07 - 2023.12")
set_font(r2, size=9.5, color=GRAY)
add_bullet(right, "授课与课程设计 —— ", "负责 Web / C++ / Python / Scratch 各方向线上授课，长期做技术拆解，能把复杂技术转化为易懂方案。")
add_bullet(right, "竞赛辅导 —— ", "辅导学生参加信息学奥赛、全国青少年编程能力等级测评，学生获省赛三等奖、国赛优胜奖。")
add_bullet(right, "技术讲解能力 —— ", "深耕 Python 等编程技术，常年向零基础学员讲清抽象概念，可迁移到 AI 方案讲解与需求沟通。", space_after=6)

p = add_para(right, space_after=2)
r1 = p.add_run("北京未科教育科技　|　Python 讲师（实习）　")
set_font(r1, size=11, bold=True)
r2 = p.add_run("2018.10 - 2019.07")
set_font(r2, size=9.5, color=GRAY)
add_bullet(right, "线上试听课、学员课时教授与夏令营 / 冬令营课程。", "", space_after=6)

# 教育背景
add_heading(right, "教育背景")
p = add_para(right, space_after=2)
r1 = p.add_run("枣庄学院　|　计算机科学与技术　|　本科　")
set_font(r1, size=11, bold=True)
r2 = p.add_run("2015.07 - 2019.06")
set_font(r2, size=9.5, color=GRAY)

# 个人总结
add_heading(right, "个人总结")
add_para(right, "计算机科班背景，独立完成完整可落地的多角色 AI Agent 项目，熟悉 RAG、LangGraph 多智能体架构、后端开发与安全优化。多年技术讲师经历，擅长业务需求拆解与复杂技术梳理输出，兼顾工程落地能力与技术表达能力，期望从事 AI 应用开发 / 大模型应用工程师岗位。",
         size=10.5, space_after=0)

doc.save(DOC_PATH)
print("已生成：", DOC_PATH)
