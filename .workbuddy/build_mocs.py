# -*- coding: utf-8 -*-
"""生成 / 补全 Obsidian MOC 索引体系。

规则：
- 顶层域（01-~07-） → MOC 名为「<域名>总览.md」
- 子目录             → MOC 名为「<目录名>.md」（可用 OVERRIDE 覆盖）
- 目录内 md 数 + 子目录数 < 2 时不建 MOC，改由父级直接链接该笔记
- 已存在的 MOC：保留原有链接顺序与正文，仅追加缺失的链接
"""
import os
import re
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TODAY = datetime.date.today().isoformat()
WIKILINK = re.compile(r"\[\[([^\]\|#]+)")

SKIP_DIRS = {".obsidian", ".workbuddy", ".git"}
# 模板文件不是笔记，不能被收进索引，也不参与元数据写入
SKIP_FILES = {"日记模板.md", "笔记模板.md"}

# 目录名 -> MOC 主文件名（不含扩展名）
OVERRIDE = {
    "01-医学学科": "医学学科总览",
    "02-科研课题": "科研课题总览",
    "03-读书笔记": "读书笔记总览",
    "04-公共课程": "公共课程总览",
    "05-校园与成长": "校园与成长总览",
    "06-日记": "日记总览",
    "07-资源库": "资源库总览",
    "《AI未来进行时》": "AI未来进行时",
    "例子": "参考案例-其他项目项目书",
}

DOMAIN_DESC = {
    "医学学科总览": "医学主干课程、形态学实验与临床早期接触记录",
    "科研课题总览": "TRIZ 电化学酰胺合成、麻醉课题组 AI 教改、分子对接与生科赛",
    "读书笔记总览": "课外阅读的章节拆解与思考",
    "公共课程总览": "英语、思政、近代史、心理健康等非医学课程",
    "校园与成长总览": "学生手册、社区、支教、保研等校园事务",
    "日记总览": "按日记录的学习与生活流水",
    "资源库总览": "Obsidian 用法、模板与工具笔记",
}


def md_files(d):
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".md"))


def sub_dirs(d):
    return sorted(x for x in os.listdir(d)
                  if os.path.isdir(os.path.join(d, x)) and x not in SKIP_DIRS)


def moc_name(dirpath):
    base = os.path.basename(dirpath)
    return OVERRIDE.get(base, base)


def build_frontmatter(title, moc_type, tags):
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    return (f"---\ntype: {moc_type}\ntitle: {title}\ntags:\n{tag_lines}\n"
            f"updated: {TODAY}\n---\n")


def nav_line(domain_title):
    if domain_title:
        return f"> 所属：[[{domain_title}]] ｜ 返回：[[00-主页|主页]]\n"
    return "> 返回：[[00-主页|主页]]\n"


def collect_prose(body_lines, linked):
    """保留非链接行（正文说明、标签行等），并剔除本脚本自己生成的脚手架行。"""
    out = []
    for ln in body_lines:
        s = ln.strip()
        if not s:
            continue
        # 脚手架：一级标题、导航引用行、目录小标题
        if s.startswith("# ") or s.startswith("> ") or s == "## 目录":
            continue
        if s.startswith("![[") or s.startswith("!["):
            out.append(s)          # 保留图片嵌入
            continue
        stripped = re.sub(r"\[\[[^\]\|#]*\]\]", "", s)
        stripped = re.sub(r"\[\[[^\]\|#]*\|[^\]]*\]\]", "", stripped)
        # 形如 "- [[x]]" / "[[x]]" / "- " 的纯链接行跳过
        if re.fullmatch(r"[-*+]?\s*", stripped):
            continue
        out.append(s)
    return out


# ---------- 第一遍：确定每个目录是否需要 MOC ----------
tree = {}   # dirpath -> dict(md=[], subs=[], moc=filename or None)
for dp, dn, fn in os.walk("."):
    parts = set(dp.split(os.sep))
    if parts & SKIP_DIRS:
        continue
    dn[:] = [x for x in dn if x not in SKIP_DIRS]
    mds = [f[:-3] for f in fn if f.endswith(".md") and f not in SKIP_FILES]
    if not mds and not dn:
        continue
    tree[os.path.normpath(dp)] = {"md": sorted(mds), "subs": sorted(dn)}

for d, info in tree.items():
    if d == ".":
        info["moc"] = None
        continue
    n = len(info["md"]) + len(info["subs"])
    # 顶层域必建；其余需 >=2
    is_domain = re.match(r"^0\d-", os.path.basename(d)) is not None
    info["moc"] = moc_name(d) if (is_domain or n >= 2) else None

# ---------- 第二遍：生成 / 更新 MOC ----------
created, updated = [], []
for d, info in sorted(tree.items()):
    if d == "." or info["moc"] is None:
        continue
    moc_base = info["moc"]
    moc_path = os.path.join(d, moc_base + ".md")

    # 该 MOC 需要链接的目标
    targets = []
    for m in info["md"]:
        if m != moc_base:
            targets.append((m, len(info["md"])))
    for s in info["subs"]:
        sub = os.path.join(d, s)
        subinfo = tree.get(sub)
        if not subinfo:
            continue
        if subinfo["moc"]:
            targets.append((subinfo["moc"], None))
        else:
            # 无 MOC：直接链接子目录内的笔记
            for m in subinfo["md"]:
                targets.append((m, None))
    seen, ordered = set(), []
    for t, _ in targets:
        if t not in seen:
            seen.add(t)
            ordered.append(t)

    # 读取已有内容
    existing_links, prose = [], []
    if os.path.exists(moc_path):
        raw = open(moc_path, encoding="utf-8").read()
        body = raw
        if body.startswith("---"):
            m = re.match(r"^---\n.*?\n---\n", body, re.S)
            if m:
                body = body[m.end():]
        for ln in body.split("\n"):
            s = ln.strip()
            # 跳过脚手架行，避免把导航目标（上级索引 / 主页）误收进目录
            if s.startswith("# ") or s.startswith("> ") or s == "## 目录":
                continue
            for lk in WIKILINK.findall(ln):
                if lk.strip() and lk.strip() not in existing_links:
                    existing_links.append(lk.strip())
        prose = collect_prose(body.split("\n"), existing_links)
        created_flag = False
    else:
        created_flag = True

    # 最终链接顺序：已有顺序优先 + 缺失项追加
    final = [x for x in existing_links if x != moc_base]
    for t in ordered:
        if t not in final:
            final.append(t)

    title = moc_base
    is_domain = re.match(r"^0\d-", os.path.basename(d)) is not None
    tags = ["索引"]
    if is_domain:
        tags.append("域索引")
        parent_title = None
    else:
        parent = os.path.dirname(d)
        parent_title = tree.get(parent, {}).get("moc") if parent else None
        if parent_title is None and parent not in ("", "."):
            parent_title = None
        tags.append(os.path.basename(d))
    if title in DOMAIN_DESC:
        tags.append("MOC")

    fm = build_frontmatter(title, "域索引" if is_domain else "专题索引", tags)
    parts = [fm, f"# {title}\n\n"]
    if is_domain and title in DOMAIN_DESC:
        parts.append(f"{DOMAIN_DESC[title]}\n\n")
    parts.append(nav_line(parent_title) + "\n")
    if prose:
        parts.append("\n".join(prose) + "\n\n")
    parts.append("## 目录\n\n")
    for lk in final:
        parts.append(f"- [[{lk}]]\n")

    content = "".join(parts)
    with open(moc_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    (created if created_flag else updated).append(moc_path)

print("新建 MOC:", len(created))
for p in created:
    print("   [新建]", p)
print("\n更新 MOC:", len(updated))
for p in updated:
    print("   [更新]", p)
