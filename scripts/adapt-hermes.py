#!/usr/bin/env python3
"""把上游 qingsheng skill（Claude Code 版）改造成 Hermes Agent 可直接安装的版本。

幂等：对同一份上游内容重复运行结果完全一致。
上游改动导致关键锚点消失时脚本直接报错退出，让同步流程失败，
而不是静默推送一个没适配好的技能。
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skill"

HERMES_SKILL_PATH = "${HERMES_HOME:-$HOME/.hermes}/skills/social-media/qingsheng"

HERMES_BLOCK = """<!-- HERMES-ADAPT:BEGIN -->
## Hermes 运行环境适配（优先级高于下文所有 Claude Code 假设）

本技能原本为 Claude Code 编写，在 Hermes Agent 中运行时按以下映射执行：

1. **读参考文件**：用 `skill_view(name='qingsheng', file_path='references/xxx.md')`。不要用 `~/.claude/skills/...` 这类绝对路径。
2. **快捷指令不是独立斜杠命令**。用户说 `/急`、`急`、`/挽回`、`/换一个`、`/展示面`、`/自动`、`/顾问`、`/复盘`、`/qingsheng-upgrade`（带不带斜杠都算）时，用 `skill_view` 读对应文件，再按文件里的流程执行：
   - 急 → `急.md`
   - 挽回 → `挽回.md`
   - 换一个 → `换一个.md`
   - 展示面 → `展示面.md`
   - 自动 → `自动.md`
   - 顾问 → 回到本文件的默认顾问模式
   - 复盘 → 按 `references/user-context.md` 的档案协议读取目标档案
   - qingsheng-upgrade → `qingsheng-upgrade.md`（本机安装目录为 `%HERMES_SKILL_PATH%/`；升级也可直接 `hermes skills install tomwong001/qingsheng-skill/skill --force`）
3. **向用户提问**用 `clarify` 工具（选项式），取代 `AskUserQuestion`。
4. **联网搜索**用 `web_search` / `web_extract`，取代 `WebSearch`。
5. **看截图/图片**先用 `vision_analyze` 打开再分析（Hermes 不能像 Claude 那样直接内联读图）；OCR 细节看不清时按 `vision_analyze` 的 region 裁剪放大。
6. **桌面应用操作**（素材采集）在 computer-use 工具可用时按 `references/user-context.md`「素材采集」执行；不可用时按原文降级路径请用户提供截图或文字。
7. **档案存储**沿用 `~/.qingsheng/`（Linux/macOS）或 `$APPDATA/.qingsheng/`（Windows），与 Claude 版共用，可迁移。

---
<!-- HERMES-ADAPT:END -->""".replace("%HERMES_SKILL_PATH%", HERMES_SKILL_PATH)

# 逐条替代规则：(说明, 正则, 替换, 是否必须命中)
RULES: list[tuple[str, str, str, bool]] = [
    (
        "升级文档里的 global/local 双路径",
        r"~?\.?/?\.?claude/skills/qingsheng-skill/?\s+← global（优先）\n\.claude/skills/qingsheng-skill/?\s+← local（项目级）",
        f"{HERMES_SKILL_PATH}/    ← Hermes 唯一安装位置",
        False,
    ),
    ("Claude 全局技能路径", r"~/\.claude/skills/qingsheng-skill", HERMES_SKILL_PATH, False),
    ("Claude 项目级技能路径", r"\.claude/skills/qingsheng-skill", HERMES_SKILL_PATH, False),
    ("AskUserQuestion → clarify", r"AskUserQuestion", "clarify", False),
    ("WebSearch → web_search", r"WebSearch", "web_search", False),
    (
        "子命令读取主技能的方式",
        r"读取情圣主技能文件 SKILL\.md",
        "用 skill_view(name='qingsheng') 读取情圣主技能 SKILL.md",
        False,
    ),
]

ANCHOR_H1 = "# 情圣 —"
MARK_BEGIN = "<!-- HERMES-ADAPT:BEGIN -->"
MARK_END = "<!-- HERMES-ADAPT:END -->"
# 原样分发、不参与改写与检查的文件（CHANGELOG 是上游历史记录，不该被改）
VERBATIM = {"CHANGELOG.md"}


def md_files() -> list[Path]:
    return [p for p in sorted(SKILL_DIR.rglob("*.md")) if p.name not in VERBATIM]



def adapt_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for label, pattern, repl, _required in RULES:
        text, n = re.subn(pattern, repl, text)
        if n:
            counts[label] = n
    return text, counts


def install_hermes_block(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    # 先删掉上一次插入的块，保证幂等
    text = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n*", "", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(ANCHOR_H1):
            head = "\n".join(lines[:i]).rstrip("\n")
            tail = "\n".join(lines[i:])
            text = f"{head}\n\n{HERMES_BLOCK}\n\n{tail}\n"
            break
    else:
        raise SystemExit(f"adapt: 找不到主标题锚点 {ANCHOR_H1!r}，上游结构可能已变")

    skill_md.write_text(text, encoding="utf-8")


def main() -> int:
    if not (SKILL_DIR / "SKILL.md").is_file():
        print(f"adapt: {SKILL_DIR}/SKILL.md 不存在", file=sys.stderr)
        return 2

    total: dict[str, int] = {}
    for path in md_files():
        new, counts = adapt_text(path.read_text(encoding="utf-8"))
        path.write_text(new, encoding="utf-8")
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v

    install_hermes_block(SKILL_DIR / "SKILL.md")

    # 版本与变更日志随技能一起分发（版本检查 preamble 要读 VERSION）
    for name in ("VERSION", "CHANGELOG.md"):
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, SKILL_DIR / name)

    # 失败即报错：适配没生效就不许提交
    problems: list[str] = []
    for path in md_files():
        body = path.read_text(encoding="utf-8")
        body = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END), "", body, flags=re.S)
        for needle in (".claude/skills/qingsheng-skill", "AskUserQuestion", "WebSearch"):
            if needle in body:
                problems.append(f"{path.relative_to(ROOT)} 仍包含 {needle}")
    if not total:
        problems.append("没有任何替代规则命中，上游结构可能已变，请检查 adapt 规则")
    if MARK_BEGIN not in (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"):
        problems.append("SKILL.md 未插入 Hermes 适配块")
    if problems:
        print("adapt 失败：\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else "?"
    print(f"adapt: 完成（上游 v{version}）")
    for label, n in sorted(total.items()):
        print(f"  - {label}: {n} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
