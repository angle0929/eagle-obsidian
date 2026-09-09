# -*- coding: utf-8 -*-
"""为全部笔记写入 YAML frontmatter、所属导航与同专题横向链接。

- 修复 7 处伪 frontmatter（--- 内嵌 markdown 标题，来自 AI 对话导出）
- 修复 1 处示例性断链（教程中演示语法的 [[笔记标题]]，改为行内代码）
- 为 13 篇日记加前后篇导航
"""
import os
import re
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TODAY = datetime.date.today().isoformat()
SKIP = {".obsidian", ".workbuddy", ".git"}
# 模板文件保持原样，不参与元数据与导航写入（否则会被复制进每篇新笔记）
SKIP_FILES = {"日记模板.md", "笔记模板.md"}

DOMAIN_MOC = {
    "01-医学学科": "医学学科总览",
    "02-科研课题": "科研课题总览",
    "03-读书笔记": "读书笔记总览",
    "04-公共课程": "公共课程总览",
    "05-校园与成长": "校园与成长总览",
    "06-日记": "日记总览",
    "07-资源库": "资源库总览",
}

HOME = "00-主页"

# 目录名与其索引页名称不一致时的映射（与 build_mocs.py 保持一致）
TOPIC_ALIAS = {
    "《AI未来进行时》": "AI未来进行时",
}


def all_md():
    out = []
    for dp, dn, fn in os.walk("."):
        if set(dp.split(os.sep)) & SKIP:
            continue
        for f in fn:
            if f.endswith(".md") and f not in SKIP_FILES:
                out.append(os.path.normpath(os.path.join(dp, f)))
    return sorted(out)


def parse_fm(text):
    """返回 (frontmatter_dict, body, had_fm)"""
    m = re.match(r"^\s*---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text, False
    blk = m.group(1)
    # 伪 frontmatter：块内含 markdown 标题 → 视为无 frontmatter
    if any(l.lstrip().startswith("#") for l in blk.split("\n")):
        return {}, text, False
    d = {}
    cur = None
    for line in blk.split("\n"):
        if re.match(r"^  - ", line):
            if cur:
                d.setdefault(cur, [])
                if isinstance(d[cur], list):
                    d[cur].append(line[4:].strip())
            continue
        mm = re.match(r"^([\w\u4e00-\u9fa5_\-]+):\s*(.*)$", line)
        if mm:
            cur = mm.group(1)
            d[cur] = mm.group(2).strip()
    return d, text[m.end():], True


def strip_pseudo_fm(text):
    """移除 AI 对话导出的伪 frontmatter，返回 (新文本, 模型名 or None)"""
    m = re.match(r"^\s*---\n##\s*🤖\s*([^\n]+)\n(.*?)\n---\n?", text, re.S)
    if m:
        model = m.group(1).strip()
        return text[m.end():], model
    m = re.match(r"^\s*---\n(.*?)\n---\n?", text, re.S)
    if m and any(l.lstrip().startswith("#") for l in m.group(1).split("\n")):
        return text[m.end():], None
    return text, None


def render_fm(d):
    order = ["title", "type", "domain", "topic", "source", "tags", "created", "updated"]
    lines = ["---"]
    for k in order:
        if k not in d:
            continue
        v = d[k]
        if isinstance(v, list):
            if not v:
                continue
            lines.append(f"{k}:")
            for x in v:
                lines.append(f"  - {x}")
        else:
            lines.append(f"{k}: {v}")
    for k, v in d.items():
        if k in order:
            continue
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def created_date(path):
    try:
        ts = min(os.path.getctime(path), os.path.getmtime(path))
    except OSError:
        ts = os.path.getmtime(path)
    return datetime.date.fromtimestamp(ts).isoformat()


def main():
    files = all_md()
    stats = {"frontmatter": 0, "nav": 0, "diary": 0, "pseudo": 0, "fixlink": 0}

    # 目录 → 同级 md（用于同专题横向链接）
    dir_md = {}
    for p in files:
        d = os.path.dirname(p)
        dir_md.setdefault(d, []).append(os.path.basename(p)[:-3])
    all_names = {os.path.basename(p)[:-3] for p in files}

    for p in files:
        raw = open(p, encoding="utf-8", errors="replace").read()
        text = raw

        # 1) 修复示例性断链
        if '"$[[笔记标题]]$"' in text:
            text = text.replace('"$[[笔记标题]]$"', '`$[[笔记标题]]$`')
            stats["fixlink"] += 1

        # 2) 去除伪 frontmatter
        text, model = strip_pseudo_fm(text)
        if model:
            stats["pseudo"] += 1

        # 2b) 幂等：先移除上一轮生成的导航块
        text = re.sub(r"\n?---\n\n> 所属：[^\n]*\n(?:> 同专题：[^\n]*\n)?", "\n", text)
        text = re.sub(r"^> ‹ 上一篇：[^\n]*\n\n", "", text, flags=re.M)
        text = re.sub(r"\n{3,}$", "\n", text)

        # 3) 解析（真实）frontmatter
        fm, body, had_fm = parse_fm(text)

        parts = p.split(os.sep)
        name = os.path.basename(p)[:-3]
        domain_dir = parts[0] if len(parts) > 1 and parts[0] in DOMAIN_MOC else None
        domain = re.sub(r"^0\d-", "", domain_dir) if domain_dir else None
        topic = parts[1] if domain_dir and len(parts) > 2 else None
        in_diary = domain_dir == "06-日记"

        # 判定类型
        if p == os.path.join("00-主页.md"):
            ntype = "主页"
        elif fm.get("type") in ("域索引", "专题索引"):
            ntype = fm["type"]
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", name):
            ntype = "日记"
        else:
            ntype = "笔记"

        # 组装 frontmatter
        new = dict(fm)
        new["title"] = fm.get("title", name)
        new["type"] = ntype
        if domain:
            new["domain"] = domain
        if topic:
            new["topic"] = topic
        if model:
            new["source"] = f"AI 生成（{model}）"
        new.setdefault("created", created_date(p))
        new["updated"] = TODAY

        tags = list(fm.get("tags", [])) if isinstance(fm.get("tags"), list) else []
        for t in ([domain] if domain else []) + ([topic] if topic else []):
            if t and t not in tags:
                tags.append(t)
        if ntype in ("域索引", "专题索引", "主页") and "索引" not in tags:
            tags.insert(0, "索引")
        if tags:
            new["tags"] = tags

        body = body.lstrip("\n")
        out = render_fm(new) + "\n" + body

        # 4) 日记前后导航
        if in_diary and ntype == "日记":
            seq = sorted(dir_md.get(os.path.dirname(p), []))
            idx = seq.index(name) if name in seq else -1
            if idx >= 0:
                prev_l = f"[[{seq[idx-1]}]]" if idx > 0 else "（最早一篇）"
                next_l = f"[[{seq[idx+1]}]]" if idx < len(seq) - 1 else "（最新一篇）"
                nav = f"> ‹ 上一篇：{prev_l} ｜ [[日记总览]] ｜ 下一篇：{next_l} ›\n\n"
                out = render_fm(new) + "\n" + nav + body
                stats["diary"] += 1

        # 5) 底部所属导航 + 同专题横向链接（MOC 与主页已有顶部导航，跳过）
        if ntype not in ("域索引", "专题索引", "主页") and domain_dir:
            dom_moc = DOMAIN_MOC[domain_dir]
            # 仅在确实存在同名索引页时才链接专题，否则退回域级
            topic_link = None
            if topic:
                if topic in all_names:
                    topic_link = topic
                elif TOPIC_ALIAS.get(topic) in all_names:
                    topic_link = TOPIC_ALIAS[topic]
            topic_seg = f" › [[{topic_link}]]" if topic_link else ""
            lines = ["\n---\n", f"\n> 所属：[[{dom_moc}]]{topic_seg} ｜ 返回：[[{HOME}|主页]]\n"]
            sibs = [] if in_diary else [x for x in dir_md.get(os.path.dirname(p), []) if x != name]
            if sibs:
                show = sibs[:6]
                link_str = " · ".join(f"[[{x}]]" for x in show)
                if len(sibs) > len(show):
                    link_str += f" …等 {len(sibs)} 篇"
                lines.append(f"> 同专题：{link_str}\n")
            out = out.rstrip("\n") + "\n" + "".join(lines)
            stats["nav"] += 1

        if out != raw:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(out)
        stats["frontmatter"] += 1

    print("处理笔记总数:", stats["frontmatter"])
    print("写入底部导航:", stats["nav"])
    print("写入日记前后导航:", stats["diary"])
    print("修复伪 frontmatter:", stats["pseudo"])
    print("修复示例断链:", stats["fixlink"])


if __name__ == "__main__":
    main()
