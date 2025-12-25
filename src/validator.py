from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "error" | "warning" | "info"
    message: str
    path: str = ""
    line: int | None = None
    col: int | None = None
    context: str | None = None


def validate_json_and_latex(json_str: str) -> tuple[Any | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if not json_str:
        return None, issues

    issues.extend(_find_suspicious_json_escapes(json_str))

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        issues.append(_json_decode_issue(json_str, e))
        return None, issues
    except Exception as e:
        issues.append(ValidationIssue(severity="error", message=f"JSON 解析异常：{e}"))
        return None, issues

    issues.extend(_validate_schema(data))
    issues.extend(_validate_all_strings(data))
    return data, issues


def extract_first_latex_error(log_path: str, tex_path: str) -> ValidationIssue | None:
    if not os.path.exists(log_path):
        return None

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            log_lines = f.read().splitlines()
    except Exception:
        return None

    err_idx = next((i for i, l in enumerate(log_lines) if l.lstrip().startswith("!")), None)
    if err_idx is None:
        return None

    err_line = log_lines[err_idx].lstrip()
    err_msg = err_line[1:].strip() if err_line.startswith("!") else err_line.strip()

    line_no = None
    for j in range(err_idx, min(err_idx + 20, len(log_lines))):
        m = re.search(r"l\.(\d+)", log_lines[j])
        if m:
            line_no = int(m.group(1))
            break

    tex_snippet = None
    if line_no is not None and os.path.exists(tex_path):
        try:
            with open(tex_path, "r", encoding="utf-8", errors="replace") as f:
                tex_lines = f.read().splitlines()
            if 1 <= line_no <= len(tex_lines):
                tex_snippet = tex_lines[line_no - 1].rstrip()
        except Exception:
            tex_snippet = None

    context = None
    if line_no is not None and tex_snippet is not None:
        context = f"TeX 行 {line_no}:\n{tex_snippet}"

    return ValidationIssue(
        severity="error",
        path="LaTeX",
        message=f"{err_msg}" + (f"（l.{line_no}）" if line_no is not None else ""),
        context=context,
    )


def _json_decode_issue(raw: str, e: json.JSONDecodeError) -> ValidationIssue:
    line = getattr(e, "lineno", None)
    col = getattr(e, "colno", None)

    context = None
    try:
        raw_lines = raw.splitlines()
        if line and 1 <= line <= len(raw_lines):
            bad_line = raw_lines[line - 1]
            caret_pos = max((col or 1) - 1, 0)
            caret = " " * caret_pos + "^"
            context = bad_line + "\n" + caret
    except Exception:
        context = None

    return ValidationIssue(
        severity="error",
        message=f"JSON 格式错误：{e.msg}",
        path="",
        line=line,
        col=col,
        context=context,
    )


def _find_suspicious_json_escapes(raw: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    # 典型误写：JSON 字符串里写成 \frac / \begin，会被当成 \f / \b 转义，JSON 仍能通过但内容会坏掉。
    # 注意：合法写法是 \\frac / \\begin（在 raw 文本里会出现 "\\\\frac" 这种序列）。
    escape_letters = {"b", "f", "n", "r", "t"}

    in_string = False
    escaped = False
    line = 1
    col = 0
    i = 0

    while i < len(raw) - 1:
        ch = raw[i]
        if ch == "\n":
            line += 1
            col = 0
            i += 1
            escaped = False
            continue

        col += 1

        if not in_string:
            if ch == '"':
                in_string = True
            i += 1
            continue

        if escaped:
            escaped = False
            i += 1
            continue

        if ch == "\\":
            escaped = True
            esc = raw[i + 1]
            nxt2 = raw[i + 2] if i + 2 < len(raw) else ""
            if esc in escape_letters and nxt2.isalpha():
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message=(
                            f"疑似未双重转义：检测到 JSON 转义 \\{esc}{nxt2}...；"
                            f"若想表示 LaTeX 命令，通常应写成 \\\\{esc}{nxt2}..."
                        ),
                        line=line,
                        col=col,
                    )
                )
            i += 1
            continue

        if ch == '"':
            in_string = False
            i += 1
            continue

        i += 1

    return issues


def _validate_schema(data: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, dict):
        return [ValidationIssue(severity="error", message="顶层必须是 JSON 对象（{...}）")]

    meta = data.get("meta")
    if meta is None or not isinstance(meta, dict):
        issues.append(
            ValidationIssue(
                severity="warning",
                path="meta",
                message="建议提供 meta 对象（title/subject 等），否则文件名自动提取可能失败",
            )
        )
    else:
        if not meta.get("title"):
            issues.append(ValidationIssue(severity="warning", path="meta.title", message="缺少 title（标题）"))
        if not meta.get("subject"):
            issues.append(ValidationIssue(severity="warning", path="meta.subject", message="缺少 subject（科目）"))

    sections = data.get("sections")
    if not isinstance(sections, list):
        issues.append(ValidationIssue(severity="error", path="sections", message="sections 必须是数组"))
        return issues

    allowed_types = {"single_choice", "multiple_choice", "fill", "problem"}
    for si, section in enumerate(sections):
        spath = f"sections[{si}]"
        if not isinstance(section, dict):
            issues.append(ValidationIssue(severity="error", path=spath, message="section 必须是对象"))
            continue
        stype = section.get("type")
        if stype not in allowed_types:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    path=f"{spath}.type",
                    message=f"type 建议为 {sorted(allowed_types)} 之一（当前：{stype!r}）",
                )
            )
        qs = section.get("questions")
        if not isinstance(qs, list):
            issues.append(ValidationIssue(severity="error", path=f"{spath}.questions", message="questions 必须是数组"))
            continue

        for qi, q in enumerate(qs):
            qpath = f"{spath}.questions[{qi}]"
            if not isinstance(q, dict):
                issues.append(ValidationIssue(severity="error", path=qpath, message="question 必须是对象"))
                continue
            if "content" not in q:
                issues.append(ValidationIssue(severity="warning", path=f"{qpath}.content", message="缺少 content"))

            if stype in {"single_choice", "multiple_choice"}:
                opts = q.get("options")
                if not isinstance(opts, list) or not opts:
                    issues.append(ValidationIssue(severity="error", path=f"{qpath}.options", message="选择题需要 options 数组，且不能为空"))

            fig = q.get("figure")
            if fig is not None and not isinstance(fig, dict):
                issues.append(ValidationIssue(severity="warning", path=f"{qpath}.figure", message="figure 建议为对象或 null"))
            if isinstance(fig, dict) and fig.get("type") == "tikz" and not isinstance(fig.get("code"), str):
                issues.append(ValidationIssue(severity="warning", path=f"{qpath}.figure.code", message="tikz figure 需要字符串 code"))

            img = q.get("image")
            if img is not None and not isinstance(img, (dict, bool, str)):
                issues.append(ValidationIssue(severity="warning", path=f"{qpath}.image", message="image 建议为对象、布尔或字符串"))
            if isinstance(img, dict):
                for key in ("width", "height"):
                    if key in img and not isinstance(img.get(key), str):
                        issues.append(ValidationIssue(severity="warning", path=f"{qpath}.image.{key}", message=f"image.{key} 建议为字符串"))

    return issues


def _validate_all_strings(data: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for path, s in _iter_strings(data):
        issues.extend(_validate_latex_string(s, path))
    return issues


def _iter_strings(obj: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            kpath = f"{path}.{k}" if path else str(k)
            yield from _iter_strings(v, kpath)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            ipath = f"{path}[{i}]"
            yield from _iter_strings(v, ipath)
    elif isinstance(obj, str):
        yield path, obj


def _validate_latex_string(s: str, path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # 明确的非 LaTeX 字段：避免误报（例如 sections[*].type = "single_choice"）
    if path.endswith(".type") or path.endswith(".id"):
        return issues

    # 1) 控制字符：常见于 \f(=\frac) / \b(=\begin) 被 JSON 转义吞掉
    bad = [c for c in s if (ord(c) < 32 and c not in "\n\r\t")]
    if bad:
        sample = " ".join(repr(c) for c in bad[:5])
        issues.append(
            ValidationIssue(
                severity="error",
                path=path,
                message=f"检测到控制字符 {sample}（疑似 JSON 中反斜杠未写成 \\\\，例如 \\\\frac / \\\\begin）",
            )
        )

    # 1.5) 含 \\n 直接报错
    if "\\n" in s:
        issues.append(
            ValidationIssue(
                severity="error",
                path=path,
                message="检测到 \\n 字符串，请移除",
            )
        )

    # 2) $ 是否成对（忽略 \$）
    dollar_count = len(re.findall(r"(?<!\\)\$", s))
    if dollar_count % 2 == 1:
        issues.append(ValidationIssue(severity="error", path=path, message="检测到未成对的 $（数学模式可能未闭合）"))

    # 3) $$ 提示（不阻断）
    if re.search(r"(?<!\\)\$\$", s):
        issues.append(
            ValidationIssue(
                severity="warning",
                path=path,
                message="检测到 $$...$$（部分模板/环境不友好，建议改用 $...$ 或 \\\\[...\\\\]）",
            )
        )

    # 4) 花括号简单配对（低成本预警）
    if s.count("{") != s.count("}"):
        issues.append(ValidationIssue(severity="warning", path=path, message="检测到 { } 数量不一致（可能存在括号未闭合）"))

    # 5) \left / \right 配对
    left_n = len(re.findall(r"\\left\b", s))
    right_n = len(re.findall(r"\\right\b", s))
    if left_n != right_n:
        issues.append(ValidationIssue(severity="warning", path=path, message="检测到 \\left 与 \\right 数量不一致"))

    # 6) begin/end 环境匹配（尽量不误报）
    issues.extend(_check_env_balance(s, path))

    # 7) 常见未转义字符（仅提示）
    # 仅检测“非数学模式”部分，避免把 $...$ / \(...\) / \[...\] 内部的下标等误报。
    non_math = _strip_math_segments(s).replace("__BLANK__", "")
    for ch, desc in [("%", "可能会注释后续内容"), ("&", "表格对齐符"), ("#", "参数符"), ("_", "下标符")]:
        if re.search(rf"(?<!\\){re.escape(ch)}", non_math):
            issues.append(ValidationIssue(severity="warning", path=path, message=f"检测到未转义的 {ch}（{desc}）"))

    return issues


def _strip_math_segments(s: str) -> str:
    patterns = [
        r"(?<!\\)\$\$.*?(?<!\\)\$\$",
        r"(?<!\\)\$.*?(?<!\\)\$",
        r"\\\(.*?\\\)",
        r"\\\[.*?\\\]",
    ]
    out = s
    for pat in patterns:
        out = re.sub(pat, "", out, flags=re.DOTALL)
    return out


def _check_env_balance(s: str, path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    begins = list(re.finditer(r"\\begin\{([^}]+)\}", s))
    ends = list(re.finditer(r"\\end\{([^}]+)\}", s))
    if not begins and not ends:
        return issues

    stack: list[str] = []
    tokens: list[tuple[int, str, str]] = []
    for m in begins:
        tokens.append((m.start(), "begin", m.group(1)))
    for m in ends:
        tokens.append((m.start(), "end", m.group(1)))
    tokens.sort(key=lambda x: x[0])

    for _, kind, name in tokens:
        if kind == "begin":
            stack.append(name)
        else:
            if not stack:
                issues.append(ValidationIssue(severity="warning", path=path, message=f"检测到 \\end{{{name}}} 但缺少对应的 \\begin"))
                continue
            top = stack.pop()
            if top != name:
                issues.append(ValidationIssue(severity="warning", path=path, message=f"环境不匹配：\\begin{{{top}}} ... \\end{{{name}}}"))

    for name in reversed(stack):
        issues.append(ValidationIssue(severity="warning", path=path, message=f"检测到 \\begin{{{name}}} 但缺少对应的 \\end"))

    return issues
