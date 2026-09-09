# -*- coding: utf-8 -*-
"""Obsidian 知识库重构脚本（一次性）。

阶段 A：删除已确认的插件噪声 / 临时文件 / 空目录
阶段 B：按七大域重排目录
阶段 C：文件级改名（统一 MOC 命名、修正错别字与全角括号）
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

log = []


def rm_path(p):
    if os.path.isdir(p):
        shutil.rmtree(p)
        log.append(("删除目录", p))
    elif os.path.isfile(p):
        os.remove(p)
        log.append(("删除文件", p))
    else:
        log.append(("跳过(不存在)", p))


def mv(src, dst):
    src = src.replace("/", os.sep)
    dst = dst.replace("/", os.sep)
    if not os.path.exists(src):
        log.append(("跳过(源不存在)", src))
        return
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.exists(dst):
        log.append(("跳过(目标已存在)", dst))
        return
    shutil.move(src, dst)
    log.append(("移动", f"{src}  ->  {dst}"))


# ============ 阶段 A：清理 ============
print("=== 阶段 A：清理插件噪声 ===")
rm_path("课题/copilot/copilot-custom-prompts")
rm_path("课题/化学/TRIZ/例子/~$t022e002+创新设计类+脑韵微探  (匿名版) .docx")
rm_path("微信")
rm_path("课题/化学/TRIZ/Attachments")

# ============ 阶段 B：目录重排 ============
print("=== 阶段 B：目录重排 ===")
DIR_MOVES = [
    # 01 医学学科
    ("系统解剖学",                    "01-医学学科/系统解剖学"),
    ("组织学与胚胎学",                "01-医学学科/组织学与胚胎学"),
    ("医学细胞生物学",                "01-医学学科/医学细胞生物学"),
    ("医学遗传学",                    "01-医学学科/医学遗传学"),
    ("医用化学",                      "01-医学学科/医用化学"),
    ("医用高等数学",                  "01-医学学科/医用高等数学"),
    ("医学实验和概念扩展",            "01-医学学科/医学实验和概念扩展"),
    # 02 科研课题
    ("课题/化学/TRIZ",                "02-科研课题/化学·TRIZ酰胺合成"),
    ("课题/麻醉课题组",               "02-科研课题/麻醉课题组·AI教学改革"),
    ("课题/化学/molecular dock",      "02-科研课题/分子对接"),
    # 03 读书笔记
    ("阅读/《AI未来进行时》",          "03-读书笔记/《AI未来进行时》"),
    # 04 公共课程
    ("大学英语(综合)",                "04-公共课程/大学英语（综合）"),
    ("大学英语（视听说）",            "04-公共课程/大学英语（视听说）"),
    ("四六级",                        "04-公共课程/四六级"),
    ("习近平新时代中国特色社会主义思想", "04-公共课程/习近平新时代中国特色社会主义思想"),
    ("中国近代史刚要",                "04-公共课程/中国近代史纲要"),
    ("心理健康教育",                  "04-公共课程/心理健康教育"),
    ("人工智能训练师",                "04-公共课程/人工智能训练师"),
    # 05 校园与成长
    ("学生手册（2025）",              "05-校园与成长/学生手册（2025）"),
    ("社区笔记",                      "05-校园与成长/社区笔记"),
    ("第七届“青鸟”支教团",       "05-校园与成长/第七届“青鸟”支教团"),
    ("图书馆",                        "05-校园与成长/图书馆"),
    # 06 日记
    ("日记存储库",                    "06-日记"),
    # 07 资源库
    ("Obsidian学习",                  "07-资源库/Obsidian学习"),
]
for s, d in DIR_MOVES:
    mv(s, d)

# ============ 阶段 C：散落文件归位 ============
print("=== 阶段 C：散落文件归位 ===")
FILE_MOVES = [
    # 根目录 -> 01 医学学科
    ("大一下早期接触临床心得体会.md", "01-医学学科/大一下早期接触临床心得体会.md"),
    # 根目录 -> 02 科研课题（麻醉教改线）
    ("final.md",                     "02-科研课题/麻醉课题组·AI教学改革/技术方案-纯文字知识库阶段方案.md"),
    ("second.md",                    "02-科研课题/麻醉课题组·AI教学改革/技术方案-云端化完整方案.md"),
    ("知识库建立方案.md",              "02-科研课题/麻醉课题组·AI教学改革/技术方案-知识库选型对比.md"),
    ("知识库搭建最终方案1.md",          "02-科研课题/麻醉课题组·AI教学改革/技术方案-最终技术方案.md"),
    ("大语言模型在临床病历结构化与智能书写中的应用.md",
                                     "02-科研课题/麻醉课题组·AI教学改革/大语言模型在临床病历结构化与智能书写中的应用.md"),
    # 课题/ 残留 -> 02 科研课题
    ("课题/copilot/copilot-conversations/Writing_TRIZ_Core_Problem@20260702_223823.md",
                                     "02-科研课题/化学·TRIZ酰胺合成/AI对话记录-TRIZ核心问题.md"),
    ("课题/化学/生科赛.md",            "02-科研课题/生科赛·NSAID双靶点/生科赛.md"),
    ("生科赛评委视角指导：NSAID双靶点药物项目PPT与论文差异化优化方案.md",
                                     "02-科研课题/生科赛·NSAID双靶点/生科赛评委视角指导-NSAID双靶点药物项目.md"),
    ("课题/未命名.md",                "07-资源库/模板与工具/DSH 智能体架构图.md"),
    # 根目录 -> 04 公共课程
    ("医学生六级备考每日任务提醒网站（附使用教程）.md", "04-公共课程/四六级/医学生六级备考每日任务提醒网站（附使用教程）.md"),
    ("医学生（四级500分）2026上半年六级高分备考规划（3.9-6.13）+ 练习题推荐.md",
                                     "04-公共课程/四六级/医学生（四级500分）2026上半年六级高分备考规划.md"),
    # 根目录 -> 05 校园与成长
    ("保研.md",                       "05-校园与成长/保研.md"),
    ("Pasted image 20251026210319.png", "05-校园与成长/Pasted image 20251026210319.png"),
    # 附件跟随笔记（修复 传统方法.md 的既有错位引用）
    ("课题/Pasted image 20260625185809.png", "02-科研课题/化学·TRIZ酰胺合成/Pasted image 20260625185809.png"),
    # 07 资源库
    ("资源库/日记模板.md",             "07-资源库/模板与工具/日记模板.md"),
    ("资源库/怎么进行演讲.md",          "07-资源库/模板与工具/怎么进行演讲.md"),
    ("资源库/资源库.md",               "07-资源库/资源库总览.md"),
]
for s, d in FILE_MOVES:
    mv(s, d)

# 文件级改名：统一 MOC 命名
RENAMES = [
    ("01-医学学科/系统解剖学/系统解剖学链接.md", "01-医学学科/系统解剖学/系统解剖学.md"),
]
for s, d in RENAMES:
    mv(s, d)

# ============ 阶段 D：清理空壳目录 ============
print("=== 阶段 D：清理空壳目录 ===")
for _ in range(6):
    removed = False
    for dp, dn, fn in os.walk(".", topdown=False):
        parts = set(dp.split(os.sep))
        if ".workbuddy" in parts or ".obsidian" in parts or ".git" in parts:
            continue
        if dp == ".":
            continue
        if not os.listdir(dp):
            os.rmdir(dp)
            log.append(("删除空目录", dp))
            removed = True
    if not removed:
        break

print("\n=== 操作明细 ===")
for kind, detail in log:
    print(f"[{kind}] {detail}")
print("\n总操作数:", len(log))
