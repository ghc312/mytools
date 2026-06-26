#!/usr/bin/env python3
"""自动更新主 README.md 的工具列表。

扫描子目录，读取每个工具的 README.md，生成工具列表表格和目录结构。
一句话运行：python scripts/update-readme.py
"""

import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
IGNORE_DIRS = {".git", "scripts", ".github", "__pycache__", ".workbuddy"}


def parse_tool_readme(readme_path: Path) -> dict | None:
    """解析工具子目录的 README.md，提取名称、描述、类型。"""
    try:
        text = readme_path.read_text(encoding="utf-8")
    except Exception:
        return None

    lines = text.strip().split("\n")

    # 提取标题（第一个 # 标题）
    name = ""
    for line in lines:
        m = re.match(r"^#\s+(.+)", line)
        if m:
            name = m.group(1).strip()
            # 去掉开头的 emoji
            name = re.sub(r"^[^\w\u4e00-\u9fff]+", "", name).strip()
            break
    if not name:
        name = readme_path.parent.name

    # 提取描述（标题后第一段有意义的文字，跳过 blockquote > 和空行）
    desc = ""
    past_title = False
    for line in lines:
        stripped = line.strip()
        if not past_title:
            if stripped.startswith("# "):
                past_title = True
            continue
        if not stripped or stripped.startswith(">") or stripped.startswith("##"):
            continue
        # 取第一句
        desc = re.sub(r"^[^\w\u4e00-\u9fff]+", "", stripped).strip()
        if len(desc) > 80:
            desc = desc[:77] + "..."
        break

    # 检测工具类型
    tool_dir = readme_path.parent
    has_py = any(tool_dir.glob("*.py"))
    has_js = any(tool_dir.glob("*.js"))
    if has_py and has_js:
        tool_type = "混合"
    elif has_py:
        tool_type = "Python"
    elif has_js:
        tool_type = "浏览器脚本"
    else:
        tool_type = "其他"

    return {
        "dir": readme_path.parent.name,
        "name": name,
        "desc": desc,
        "type": tool_type,
    }


def scan_tools() -> list[dict]:
    """扫描所有工具子目录。"""
    tools = []
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir() or entry.name in IGNORE_DIRS or entry.name.startswith("."):
            continue
        readme = entry / "README.md"
        if readme.exists():
            info = parse_tool_readme(readme)
            if info:
                tools.append(info)
    return tools


def generate_table(tools: list[dict]) -> str:
    """生成工具列表表格。"""
    rows = ["| 工具 | 说明 | 类型 |", "|------|------|------|"]
    for t in tools:
        rows.append(
            f"| [{t['name']}](./{t['dir']}/) | {t['desc']} | {t['type']} |"
        )
    return "\n".join(rows)


def generate_tree(tools: list[dict]) -> str:
    """生成目录结构。"""
    lines = ["```", "mytools/", "├── README.md"]
    for i, t in enumerate(tools):
        prefix = "└──" if i == len(tools) - 1 else "├──"
        lines.append(f"{prefix} {t['dir']}/")
    lines.append("```")
    return "\n".join(lines)


def main():
    tools = scan_tools()

    if not tools:
        print("⚠️  没有找到工具子目录")
        return

    print(f"📋 扫描到 {len(tools)} 个工具：")
    for t in tools:
        print(f"   {t['dir']:<30} → {t['name']}")

    # 读取现有 README
    content = README.read_text(encoding="utf-8")

    # 替换工具表格（在 <!-- TOOLS_START --> 和 <!-- TOOLS_END --> 之间）
    table = generate_table(tools)
    content = re.sub(
        r"<!-- TOOLS_START -->.*<!-- TOOLS_END -->",
        f"<!-- TOOLS_START -->\n{table}\n<!-- TOOLS_END -->",
        content,
        flags=re.DOTALL,
    )

    # 替换目录树（在 <!-- TREE_START --> 和 <!-- TREE_END --> 之间）
    tree = generate_tree(tools)
    content = re.sub(
        r"<!-- TREE_START -->.*<!-- TREE_END -->",
        f"<!-- TREE_START -->\n{tree}\n<!-- TREE_END -->",
        content,
        flags=re.DOTALL,
    )

    README.write_text(content, encoding="utf-8")
    print(f"\n✅ 已更新 {README}")


if __name__ == "__main__":
    main()
