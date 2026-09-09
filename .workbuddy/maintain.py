# -*- coding: utf-8 -*-
"""Obsidian 知识库例行维护入口（可反复安全运行）。

流程：
  1. 重建/补全三级索引（build_mocs.py）
  2. 补全 frontmatter、所属导航、同专题互链、日记前后链（build_metadata.py）
  3. 体检：散落文件 / 孤立笔记 / 断链 / 元数据缺失
  4. 输出报告到 .workbuddy/维护记录/<日期>.md
"""
import os
import re
import sys
import subprocess
import datetime
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TODAY = datetime.date.today().isoformat()
SKIP_DIRS = {".obsidian", ".workbuddy", ".git"}
SKIP_FILES = {"日记模板.md", "笔记模板.md"}
EXT = {".md", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".pdf", ".docx", ".ris",
       ".canvas", ".gif", ".svg", ".webp"}
DOMAIN_RE = re.compile(r"^0\d-")

WIKILINK = re.compile(r"\[\[([^\]\|#]+)")
CODE = re.compile(r"`[^`]*`|```.*?```", re.S)


def run(name):
    print(f"--- 执行 {name} ---")
    r = subprocess.run([sys.executable, os.path.join(".workbuddy", name)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.strip())
    if r.returncode != 0:
        print("[错误]", r.stderr.strip())
    return r.returncode


def collect():
    files, md = [], []
    for dp, dn, fn in os.walk("."):
        if set(dp.split(os.sep)) & SKIP_DIRS:
            continue
        for f in fn:
            p = os.path.normpath(os.path.join(dp, f))
            files.append(p)
            if f.endswith(".md") and f not in SKIP_FILES:
                md.append(p)
    return files, sorted(md)


def check(files, md):
    issues = collections.OrderedDict()

    # 1) 根目录散落文件
    stray = [f for f in os.listdir(".")
             if os.path.isfile(f) and f != "00-主页.md" and not f.endswith(".base")]
    issues["根目录散落文件"] = stray

    # 2) 空目录
    empty = []
    for dp, dn, fn in os.walk("."):
        if set(dp.split(os.sep)) & SKIP_DIRS or dp == ".":
            continue
        if not os.listdir(dp):
            empty.append(os.path.normpath(dp))
    issues["空目录"] = empty

    # 3) 元数据缺失 / 越界
    no_fm, no_nav = [], []
    for p in md:
        t = open(p, encoding="utf-8", errors="replace").read()
        if os.path.basename(p) == "00-主页.md":   # 主页本身无需返回链接
            continue
        if not t.startswith("---"):
            no_fm.append(p)
        elif "00-主页" in t:            # 含主页链接即视为已接入
            continue
        elif "type: 域索引" in t or "type: 专题索引" in t:
            continue
        else:
            no_nav.append(p)
    issues["缺少 frontmatter"] = no_fm
    issues["缺少返回导航"] = no_nav

    # 4) 断链与孤立
    name = collections.defaultdict(list)
    for p in files:
        name[os.path.basename(p)].append(p)
    broken = collections.Counter()
    where = collections.defaultdict(list)
    incoming = collections.defaultdict(set)
    outgoing = {}
    for p in md:
        raw = open(p, encoding="utf-8", errors="replace").read()
        t = CODE.sub("", raw)
        ls = WIKILINK.findall(t)
        outgoing[p] = ls
        for l in ls:
            tgt = l if os.path.splitext(l)[1].lower() in EXT else l + ".md"
            hit = name.get(tgt) or name.get(os.path.basename(tgt))
            if hit:
                for c in hit:
                    incoming[c].add(p)
            else:
                broken[l] += 1
                where[l].append(p)
    issues["断链"] = [f"{k}  (被引用 {v} 次，例：{where[k][0]})" for k, v in broken.most_common()]
    orphans = [p for p in md if not outgoing.get(p) and not incoming.get(p)]
    issues["完全孤立笔记"] = orphans

    return issues, len(md), sum(len(v) for v in outgoing.values())


def write_report(issues, n_md, n_link):
    os.makedirs(os.path.join(".workbuddy", "维护记录"), exist_ok=True)
    path = os.path.join(".workbuddy", "维护记录", f"{TODAY}.md")
    ok = not any(issues.values())
    lines = [f"# 知识库维护报告 · {TODAY}", ""]
    lines.append(f"- 笔记数：**{n_md}**")
    lines.append(f"- 链接总数：**{n_link}**")
    lines.append(f"- 体检结果：**{'全部通过' if ok else '发现 ' + str(sum(len(v) for v in issues.values())) + ' 项待处理'}**")
    lines.append("")
    for k, v in issues.items():
        flag = "通过" if not v else f"**{len(v)} 项**"
        lines.append(f"## {k} — {flag}")
        lines.append("")
        if v:
            for x in v[:50]:
                lines.append(f"- `{x}`")
            if len(v) > 50:
                lines.append(f"- ……另有 {len(v)-50} 项")
        else:
            lines.append("无。")
        lines.append("")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    return path


def main():
    run("build_mocs.py")
    run("build_metadata.py")
    files, md = collect()
    issues, n_md, n_link = check(files, md)
    path = write_report(issues, n_md, n_link)
    print("\n=== 体检 ===")
    for k, v in issues.items():
        print(f"  {k}: {'0 ✓' if not v else str(len(v)) + ' 项'}")
        for x in v[:10]:
            print("      -", x)
    print(f"\n报告已写入: {path}")


if __name__ == "__main__":
    main()
