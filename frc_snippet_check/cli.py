"""Scan Markdown files for Java code blocks that use removed or deprecated WPILib APIs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __version__

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
SKIP_DIRS = {".git", "node_modules", "build", ".gradle", "vendor", "site-packages"}
JAVA_LANGS = {"java"}
TAG = "frc-check"
SKIP_BLOCK_TAGS = {"frc-check:skip", "frc-check-skip"}
IGNORE_LINE = "frc-check:ignore"
FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")  # indented fences: MkDocs tabs, lists


@dataclass
class CodeBlock:
    path: str
    start_line: int  # 1-based line of the first code line
    lang: str
    info: str
    lines: list[str]

    @property
    def tagged(self) -> bool:
        return TAG in self.info.split()


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    severity: str
    message: str
    fix: str
    code: str


@dataclass
class Rule:
    id: str
    severity: str
    pattern: re.Pattern
    message: str
    fix: str


def load_rules(path: Path | None = None) -> list[Rule]:
    path = path or Path(__file__).with_name("rules.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Rule(r["id"], r["severity"], re.compile(r["pattern"]), r["message"], r.get("fix", ""))
        for r in data["rules"]
    ]


def extract_blocks(text: str, path: str) -> list[CodeBlock]:
    """Return fenced code blocks (``` or ~~~) from Markdown text."""
    blocks: list[CodeBlock] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        fence, info = m.group(2), m.group(3).strip()
        if fence[0] == "`" and "`" in info:  # not a valid fence opener
            i += 1
            continue
        lang = info.split()[0].lower() if info else ""
        lang = lang.split("{")[0]
        body: list[str] = []
        j = i + 1
        while j < len(lines):
            close = FENCE_RE.match(lines[j])
            if close and close.group(2)[0] == fence[0] and len(close.group(2)) >= len(fence) and not close.group(3).strip():
                break
            body.append(lines[j])
            j += 1
        blocks.append(CodeBlock(path, i + 2, lang, info, body))
        i = j + 1
    return blocks


def iter_markdown_files(paths: list[str]):
    for p in paths:
        root = Path(p)
        if root.is_file():
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if Path(name).suffix.lower() in MARKDOWN_SUFFIXES:
                    yield Path(dirpath) / name


def check_block(block: CodeBlock, rules: list[Rule]) -> list[Finding]:
    findings = []
    for offset, line in enumerate(block.lines):
        if IGNORE_LINE in line:
            continue
        for rule in rules:
            if rule.pattern.search(line):
                findings.append(
                    Finding(block.path, block.start_line + offset, rule.id, rule.severity,
                            rule.message, rule.fix, line.strip())
                )
    return findings


def scan(paths: list[str], rules: list[Rule], only_tagged: bool = False):
    files = blocks_checked = 0
    findings: list[Finding] = []
    for md in iter_markdown_files(paths):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files += 1
        for block in extract_blocks(text, str(md)):
            if block.lang not in JAVA_LANGS:
                continue
            if SKIP_BLOCK_TAGS & set(block.info.split()):
                continue
            if only_tagged and not block.tagged:
                continue
            blocks_checked += 1
            findings.extend(check_block(block, rules))
    return files, blocks_checked, findings


def _gh_escape(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def render(findings: list[Finding], files: int, blocks: int, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({"files": files, "java_blocks": blocks,
                           "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False)
    out = []
    for f in findings:
        if fmt == "github":
            level = "error" if f.severity == "error" else "warning"
            out.append(f"::{level} file={f.path},line={f.line},title=frc-snippet-check {f.rule}::"
                       + _gh_escape(f"{f.message} {f.fix}"))
        else:
            out.append(f"{f.path}:{f.line}: {f.severity}: [{f.rule}] {f.message}\n"
                       f"    {f.code}\n    fix: {f.fix}")
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    out.append(f"Checked {blocks} Java code block(s) in {files} Markdown file(s): "
               f"{errors} error(s), {warnings} warning(s).")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="frc-snippet-check", description=__doc__)
    ap.add_argument("paths", nargs="*", default=["."], help="Files or folders to scan (default: .)")
    ap.add_argument("--only-tagged", action="store_true",
                    help=f"Only check code blocks whose info string contains '{TAG}'")
    ap.add_argument("--format", choices=["text", "github", "json"], default="text")
    ap.add_argument("--fail-on", choices=["error", "warning", "never"], default="error",
                    help="Exit with status 1 when findings at this level or above exist (default: error)")
    ap.add_argument("--rules", type=Path, help="Use a custom rules.json")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    rules = load_rules(args.rules)
    files, blocks, findings = scan(args.paths, rules, args.only_tagged)
    print(render(findings, files, blocks, args.format))

    if args.fail_on == "never":
        return 0
    if args.fail_on == "warning":
        return 1 if findings else 0
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
