from __future__ import annotations

import bisect
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

    def format_gcc_style(self, filename: str = "<json>") -> str:
        parts = []
        loc = ""
        if self.line is not None:
            loc = f"{self.line}"
            if self.col is not None:
                loc += f":{self.col}"

        severity_map = {"error": "错误", "warning": "警告", "info": "注意"}
        sev = severity_map.get(self.severity, self.severity)
        if loc:
            parts.append(f"{loc}: {sev}: {self.message}")
        else:
            parts.append(f"{sev}: {self.message}")

        if self.context:
            for ctx_line in self.context.split("\n"):
                parts.append(f"    {ctx_line}")

        return "\n".join(parts)

    def format_gcc_style_color(self, filename: str = "<json>") -> str:
        RED = "\033[1;31m"
        MAGENTA = "\033[1;35m"
        CYAN = "\033[1;36m"
        GREEN = "\033[1;32m"
        RESET = "\033[0m"
        BOLD = "\033[1m"

        parts = []
        loc = filename
        if self.path:
            loc = f"{filename}:{self.path}"
        if self.line is not None:
            loc += f":{self.line}"
            if self.col is not None:
                loc += f":{self.col}"

        if self.severity == "error":
            sev_str = f"{RED}错误{RESET}"
        elif self.severity == "warning":
            sev_str = f"{MAGENTA}警告{RESET}"
        else:
            sev_str = f"{CYAN}注意{RESET}"

        parts.append(f"{BOLD}{loc}:{RESET} {sev_str}: {self.message}")

        if self.context:
            ctx_lines = self.context.split("\n")
            for i, ctx_line in enumerate(ctx_lines):
                if i == len(ctx_lines) - 1 and ctx_line.strip().startswith("^"):
                    parts.append(f"    {GREEN}{ctx_line}{RESET}")
                else:
                    parts.append(f"    {ctx_line}")

        return "\n".join(parts)


def _display_width(s: str) -> int:
    """Calculate display width considering wide characters (CJK, etc.)."""
    import unicodedata
    width = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            width += 2
        else:
            width += 1
    return width


def format_issues_gcc_style(
    issues: list["ValidationIssue"],
    source: str = "",
    filename: str = "<json>",
    color: bool = False,
    context_chars: int = 25,
) -> str:
    if not issues:
        return ""

    source_lines = source.split("\n") if source else []
    output = []

    for issue in issues:
        ctx = issue.context
        if ctx is None and issue.line is not None and source_lines:
            line_idx = issue.line - 1
            if 0 <= line_idx < len(source_lines):
                src_line = source_lines[line_idx]
                col = issue.col or 1
                col_idx = col - 1

                start = max(0, col_idx - context_chars)
                end = min(len(src_line), col_idx + context_chars + 1)

                snippet = src_line[start:end]
                prefix = "..." if start > 0 else ""
                suffix = "..." if end < len(src_line) else ""

                display_line = f"{prefix}{snippet}{suffix}"
                caret_offset = _display_width(prefix) + _display_width(src_line[start:col_idx])
                caret = " " * caret_offset + "^"
                ctx = f"{display_line}\n{caret}"

        issue_with_ctx = ValidationIssue(
            severity=issue.severity,
            message=issue.message,
            path=issue.path,
            line=issue.line,
            col=issue.col,
            context=ctx,
        )

        if color:
            output.append(issue_with_ctx.format_gcc_style_color(filename))
        else:
            output.append(issue_with_ctx.format_gcc_style(filename))

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    summary_parts = []
    if error_count:
        summary_parts.append(f"{error_count} 个错误")
    if warning_count:
        summary_parts.append(f"{warning_count} 个警告")

    if summary_parts:
        output.append(f"\n共 {'、'.join(summary_parts)}。")

    return "\n".join(output)


def validate_json_and_latex(json_str: str) -> tuple[Any | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if not json_str:
        return None, issues

    issues.extend(_find_suspicious_json_escapes(json_str))

    def _reject_non_standard(constant: str) -> None:
        """Reject non-standard JSON values like NaN, Infinity."""
        raise ValueError(f"非标准 JSON 值：{constant}")

    try:
        data = json.loads(json_str, parse_constant=_reject_non_standard)
    except json.JSONDecodeError as e:
        issues.append(_json_decode_issue(json_str, e))
        return None, issues
    except Exception as e:
        issues.append(ValidationIssue(severity="error", message=f"JSON 解析异常：{e}"))
        return None, issues

    issues.extend(_validate_schema(data))
    issues.extend(_validate_all_strings(data, json_str))
    return data, issues


def extract_first_latex_error(log_path: str, tex_path: str) -> ValidationIssue | None:
    if not os.path.exists(log_path):
        return None

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            log_lines = f.read().splitlines()
    except Exception:
        return None

    err_idx = None
    for i, log_line in enumerate(log_lines):
        if log_line.lstrip().startswith("!"):
            err_idx = i
            break
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


LATEX_CONTENT_FIELDS = {"content", "options", "solution", "analysis", "answer", "code"}


def _is_latex_field(path: str) -> bool:
    parts = path.split(".")
    return any(p.rstrip("[]0123456789") in LATEX_CONTENT_FIELDS for p in parts)


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
            if esc == "n":
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message="检测到 \\n 转义（会被解析成换行），请移除或改写",
                        line=line,
                        col=col,
                    )
                )
            elif esc == "\\" and nxt2 == "n":
                nxt3 = raw[i + 3] if i + 3 < len(raw) else ""
                if not nxt3.isalpha():
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            message="检测到字面量 \\n（若表示换行，建议用 \\newline 或 \\\\）",
                            line=line,
                            col=col,
                        )
                    )
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


def _validate_all_strings(data: Any, raw: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    locator = _StringLocator(raw)
    for path, s in _iter_strings(data):
        line, col = locator.locate(path, s)
        issues.extend(_validate_latex_string(s, path, line=line, col=col))
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


def _count_backslashes_before(s: str, pos: int) -> int:
    count = 0
    idx = pos - 1
    while idx >= 0 and s[idx] == "\\":
        count += 1
        idx -= 1
    return count


def _scan_latex_structure(s: str) -> dict:
    unescaped_dollars: list[int] = []
    double_dollars: list[int] = []
    unescaped_open_braces: list[int] = []
    unescaped_close_braces: list[int] = []
    comment_ranges: list[tuple[int, int]] = []
    inline_math_ranges: list[tuple[int, int]] = []
    display_math_ranges: list[tuple[int, int]] = []

    backslash_run = 0
    inline_start: int | None = None
    display_start: int | None = None
    i = 0
    length = len(s)

    while i < length:
        ch = s[i]
        escaped = backslash_run % 2 == 1

        if ch == "\\":
            if not escaped and i + 1 < length:
                nxt = s[i + 1]
                if nxt == "(" and inline_start is None and display_start is None:
                    inline_start = i
                elif nxt == "[" and inline_start is None and display_start is None:
                    display_start = i
                elif nxt == ")" and inline_start is not None:
                    inline_math_ranges.append((inline_start, i + 2))
                    inline_start = None
                elif nxt == "]" and display_start is not None:
                    display_math_ranges.append((display_start, i + 2))
                    display_start = None

            backslash_run += 1
            i += 1
            continue

        if ch == "%" and not escaped:
            end = s.find("\n", i)
            if end == -1:
                end = length
            comment_ranges.append((i, end))
            backslash_run = 0
            i = end
            continue

        if ch == "$" and not escaped:
            if i + 1 < length and s[i + 1] == "$":
                unescaped_dollars.append(i)
                unescaped_dollars.append(i + 1)
                double_dollars.append(i)
                backslash_run = 0
                i += 2
                continue
            unescaped_dollars.append(i)
            backslash_run = 0
            i += 1
            continue

        if ch == "{" and not escaped:
            unescaped_open_braces.append(i)
        elif ch == "}" and not escaped:
            unescaped_close_braces.append(i)

        backslash_run = 0
        i += 1

    return {
        "unescaped_dollars": unescaped_dollars,
        "double_dollars": double_dollars,
        "unescaped_open_braces": unescaped_open_braces,
        "unescaped_close_braces": unescaped_close_braces,
        "comment_ranges": comment_ranges,
        "inline_math_ranges": inline_math_ranges,
        "display_math_ranges": display_math_ranges,
    }


def _strip_comments(s: str) -> str:
    scan = _scan_latex_structure(s)
    ranges = scan["comment_ranges"]
    if not ranges:
        return s

    out: list[str] = []
    last = 0
    for start, end in ranges:
        out.append(s[last:start])
        last = end
    out.append(s[last:])
    return "".join(out)


VERBATIM_ENVS = {"verbatim", "lstlisting", "minted", "Verbatim"}


def _strip_verbatim(s: str) -> str:
    for env in VERBATIM_ENVS:
        pattern = rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}"
        s = re.sub(pattern, "", s, flags=re.DOTALL)
    verb_pattern = r"\\verb\|[^|]*\|"
    s = re.sub(verb_pattern, "", s)
    return s


def _validate_latex_string(s: str, path: str, line: int | None = None, col: int | None = None) -> list[ValidationIssue]:
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
                line=line,
                col=col,
                message=f"检测到控制字符 {sample}（疑似 JSON 中反斜杠未写成 \\\\，例如 \\\\frac / \\\\begin）",
            )
        )

    cleaned = _strip_verbatim(_strip_comments(s))
    scan = _scan_latex_structure(cleaned)

    # 2) $ 是否成对（忽略 \$）
    dollar_count = len(scan["unescaped_dollars"])
    if dollar_count % 2 == 1:
        issues.append(ValidationIssue(severity="error", path=path, line=line, col=col, message="检测到未成对的 $（数学模式可能未闭合）"))

    # 3) $$ 提示（不阻断）
    if scan["double_dollars"]:
        issues.append(
            ValidationIssue(
                severity="warning",
                path=path,
                line=line,
                col=col,
                message="检测到 $$...$$（部分模板/环境不友好，建议改用 $...$ 或 \\\\[...\\\\]）",
            )
        )

    # 4) 花括号简单配对（低成本预警）
    if len(scan["unescaped_open_braces"]) != len(scan["unescaped_close_braces"]):
        issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message="检测到 { } 数量不一致（可能存在括号未闭合）"))

    # 5) \left / \right 配对与顺序检查
    left_matches = list(re.finditer(r"\\left\b", cleaned))
    right_matches = list(re.finditer(r"\\right\b", cleaned))
    if len(left_matches) != len(right_matches):
        issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message="检测到 \\left 与 \\right 数量不一致"))
    else:
        delim_tokens = [(m.start(), "left") for m in left_matches] + [(m.start(), "right") for m in right_matches]
        delim_tokens.sort(key=lambda x: x[0])
        delim_stack = 0
        for _, kind in delim_tokens:
            if kind == "left":
                delim_stack += 1
            else:
                delim_stack -= 1
                if delim_stack < 0:
                    issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message="检测到 \\right 出现在 \\left 之前"))
                    break

    # 5b) \(...\) 和 \[...\] 配对检查
    inline_open = len(scan["inline_math_ranges"])
    if inline_open > 0:
        pass
    inline_open_count = len(re.findall(r"(?<!\\)\\\(", cleaned))
    inline_close_count = len(re.findall(r"(?<!\\)\\\)", cleaned))
    if inline_open_count != inline_close_count:
        issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message="检测到 \\( 与 \\) 数量不一致"))

    display_open_count = len(re.findall(r"(?<!\\)\\\[", cleaned))
    display_close_count = len(re.findall(r"(?<!\\)\\\]", cleaned))
    if display_open_count != display_close_count:
        issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message="检测到 \\[ 与 \\] 数量不一致"))

    # 6) begin/end 环境匹配（尽量不误报）
    issues.extend(_check_env_balance(cleaned, path, line=line, col=col))

    # 7) 常见未转义字符（仅提示）- 在原始字符串中查找，跳过数学模式
    math_ranges = _get_all_math_ranges(scan)
    # (字符, 描述, 修复提示)
    special_chars = [
        ("%", "可能会注释后续内容", "转义为 \\\\%，或放入数学模式 $...\\\\%...$"),
        ("&", "表格对齐符", "转义为 \\\\&"),
        ("#", "参数符", "转义为 \\\\#"),
        ("_", "下标符", "若为下标如 l_1，应包裹为 $l_1$；若需字面下划线，转义为 \\\\_"),
    ]
    for ch, desc, hint in special_chars:
        pos = _find_unescaped_outside_math(cleaned, ch, math_ranges)
        if pos is not None:
            adjusted_col = (col + pos) if col is not None else col
            issues.append(ValidationIssue(severity="warning", path=path, line=line, col=adjusted_col, message=f"检测到未转义的 {ch}（{desc}）。{hint}"))

    # 8) Unicode 数学符号检测
    issues.extend(_check_unicode_math_symbols(s, path, line=line, col=col))

    return issues


UNICODE_MATH_SYMBOLS = {
    # 运算符
    "×": "\\times",
    "÷": "\\div",
    "±": "\\pm",
    "∓": "\\mp",
    "·": "\\cdot",
    "√": "\\sqrt",
    "∑": "\\sum",
    "∏": "\\prod",
    "∫": "\\int",
    "∬": "\\iint",
    "∭": "\\iiint",
    "∞": "\\infty",
    # 关系符
    "≤": "\\le 或 \\leq",
    "≥": "\\ge 或 \\geq",
    "≠": "\\ne 或 \\neq",
    "≈": "\\approx",
    "≡": "\\equiv",
    "∝": "\\propto",
    "≪": "\\ll",
    "≫": "\\gg",
    # 集合论
    "∈": "\\in",
    "∉": "\\notin",
    "∋": "\\ni",
    "⊂": "\\subset",
    "⊃": "\\supset",
    "⊆": "\\subseteq",
    "⊇": "\\supseteq",
    "∪": "\\cup",
    "∩": "\\cap",
    "∅": "\\emptyset",
    # 逻辑符号
    "∧": "\\land 或 \\wedge",
    "∨": "\\lor 或 \\vee",
    "¬": "\\neg 或 \\lnot",
    "∀": "\\forall",
    "∃": "\\exists",
    "∄": "\\nexists",
    # 箭头
    "→": "\\to 或 \\rightarrow",
    "←": "\\leftarrow",
    "↔": "\\leftrightarrow",
    "⇒": "\\Rightarrow",
    "⇐": "\\Leftarrow",
    "⇔": "\\Leftrightarrow",
    "↑": "\\uparrow",
    "↓": "\\downarrow",
    "↗": "\\nearrow",
    "↘": "\\searrow",
    "↙": "\\swarrow",
    "↖": "\\nwarrow",
    "⟹": "\\Longrightarrow",
    "⟸": "\\Longleftarrow",
    "⟺": "\\Longleftrightarrow",
    # 几何符号
    "△": "\\triangle",
    "▲": "\\blacktriangle",
    "▽": "\\triangledown 或 \\nabla",
    "▼": "\\blacktriangledown",
    "∠": "\\angle",
    "∟": "\\angle（直角）",
    "⊥": "\\perp",
    "∥": "\\parallel",
    "∦": "\\nparallel",
    "∽": "\\backsim（相似）",
    "≌": "\\cong（全等）",
    "⌒": "\\frown（弧）",
    "○": "\\circ 或 \\bigcirc",
    "●": "\\bullet",
    "□": "\\square",
    "■": "\\blacksquare",
    "◇": "\\diamond",
    "◆": "\\blacklozenge",
    "⊙": "\\odot",
    "⊕": "\\oplus",
    "⊗": "\\otimes",
    # 希腊字母（小写）
    "α": "\\alpha",
    "β": "\\beta",
    "γ": "\\gamma",
    "δ": "\\delta",
    "ε": "\\epsilon 或 \\varepsilon",
    "ζ": "\\zeta",
    "η": "\\eta",
    "θ": "\\theta",
    "ι": "\\iota",
    "κ": "\\kappa",
    "λ": "\\lambda",
    "μ": "\\mu",
    "ν": "\\nu",
    "ξ": "\\xi",
    "π": "\\pi",
    "ρ": "\\rho",
    "σ": "\\sigma",
    "τ": "\\tau",
    "υ": "\\upsilon",
    "φ": "\\phi 或 \\varphi",
    "χ": "\\chi",
    "ψ": "\\psi",
    "ω": "\\omega",
    # 希腊字母（大写）
    "Γ": "\\Gamma",
    "Δ": "\\Delta",
    "Θ": "\\Theta",
    "Λ": "\\Lambda",
    "Ξ": "\\Xi",
    "Π": "\\Pi",
    "Σ": "\\Sigma",
    "Υ": "\\Upsilon",
    "Φ": "\\Phi",
    "Ψ": "\\Psi",
    "Ω": "\\Omega",
    # 上标数字
    "⁰": "$^0$",
    "¹": "$^1$",
    "²": "$^2$",
    "³": "$^3$",
    "⁴": "$^4$",
    "⁵": "$^5$",
    "⁶": "$^6$",
    "⁷": "$^7$",
    "⁸": "$^8$",
    "⁹": "$^9$",
    "⁺": "$^+$",
    "⁻": "$^-$",
    "⁼": "$^=$",
    "⁽": "$^($",
    "⁾": "$^)$",
    "ⁿ": "$^n$",
    "ⁱ": "$^i$",
    # 下标数字
    "₀": "$_0$",
    "₁": "$_1$",
    "₂": "$_2$",
    "₃": "$_3$",
    "₄": "$_4$",
    "₅": "$_5$",
    "₆": "$_6$",
    "₇": "$_7$",
    "₈": "$_8$",
    "₉": "$_9$",
    "₊": "$_+$",
    "₋": "$_-$",
    "₌": "$_=$",
    "₍": "$_($",
    "₎": "$_)$",
    "ₐ": "$_a$",
    "ₑ": "$_e$",
    "ₒ": "$_o$",
    "ₓ": "$_x$",
    "ₕ": "$_h$",
    "ₖ": "$_k$",
    "ₗ": "$_l$",
    "ₘ": "$_m$",
    "ₙ": "$_n$",
    "ₚ": "$_p$",
    "ₛ": "$_s$",
    "ₜ": "$_t$",
    # 其他常用
    "′": "'（撇号，用 $'$ 或 $\\prime$）",
    "″": "''（双撇号，用 $''$）",
    "‰": "\\textperthousand 或 \\permil",
    "°": "\\degree 或 ^\\circ",
    "℃": "\\celsius 或 ^\\circ\\text{C}",
    "ℓ": "\\ell",
    "ℕ": "\\mathbb{N}",
    "ℤ": "\\mathbb{Z}",
    "ℚ": "\\mathbb{Q}",
    "ℝ": "\\mathbb{R}",
    "ℂ": "\\mathbb{C}",
}

UNICODE_REPLACEMENTS = {
    "×": "\\\\times ", "÷": "\\\\div ", "±": "\\\\pm ", "∓": "\\\\mp ", "·": "\\\\cdot ",
    "√": "\\\\sqrt", "∑": "\\\\sum ", "∏": "\\\\prod ", "∫": "\\\\int ", "∬": "\\\\iint ", "∭": "\\\\iiint ", "∞": "\\\\infty ",
    "≤": "\\\\le ", "≥": "\\\\ge ", "≠": "\\\\ne ", "≈": "\\\\approx ", "≡": "\\\\equiv ", "∝": "\\\\propto ", "≪": "\\\\ll ", "≫": "\\\\gg ",
    "∈": "\\\\in ", "∉": "\\\\notin ", "∋": "\\\\ni ", "⊂": "\\\\subset ", "⊃": "\\\\supset ",
    "⊆": "\\\\subseteq ", "⊇": "\\\\supseteq ", "∪": "\\\\cup ", "∩": "\\\\cap ", "∅": "\\\\emptyset ",
    "∧": "\\\\land ", "∨": "\\\\lor ", "¬": "\\\\neg ", "∀": "\\\\forall ", "∃": "\\\\exists ", "∄": "\\\\nexists ",
    "→": "\\\\to ", "←": "\\\\leftarrow ", "↔": "\\\\leftrightarrow ",
    "⇒": "\\\\Rightarrow ", "⇐": "\\\\Leftarrow ", "⇔": "\\\\Leftrightarrow ",
    "↑": "\\\\uparrow ", "↓": "\\\\downarrow ", "↗": "\\\\nearrow ", "↘": "\\\\searrow ", "↙": "\\\\swarrow ", "↖": "\\\\nwarrow ",
    "⟹": "\\\\Longrightarrow ", "⟸": "\\\\Longleftarrow ", "⟺": "\\\\Longleftrightarrow ",
    "△": "\\\\triangle ", "▲": "\\\\blacktriangle ", "▽": "\\\\nabla ", "▼": "\\\\blacktriangledown ",
    "∠": "\\\\angle ", "∟": "\\\\angle ", "⊥": "\\\\perp ", "∥": "\\\\parallel ", "∦": "\\\\nparallel ",
    "∽": "\\\\sim ", "≌": "\\\\cong ", "⌒": "\\\\frown ",
    "○": "\\\\circ ", "●": "\\\\bullet ", "□": "\\\\square ", "■": "\\\\blacksquare ",
    "◇": "\\\\diamond ", "◆": "\\\\blacklozenge ", "⊙": "\\\\odot ", "⊕": "\\\\oplus ", "⊗": "\\\\otimes ",
    "α": "\\\\alpha ", "β": "\\\\beta ", "γ": "\\\\gamma ", "δ": "\\\\delta ", "ε": "\\\\varepsilon ",
    "ζ": "\\\\zeta ", "η": "\\\\eta ", "θ": "\\\\theta ", "ι": "\\\\iota ", "κ": "\\\\kappa ",
    "λ": "\\\\lambda ", "μ": "\\\\mu ", "ν": "\\\\nu ", "ξ": "\\\\xi ", "π": "\\\\pi ",
    "ρ": "\\\\rho ", "σ": "\\\\sigma ", "τ": "\\\\tau ", "υ": "\\\\upsilon ", "φ": "\\\\varphi ",
    "χ": "\\\\chi ", "ψ": "\\\\psi ", "ω": "\\\\omega ",
    "Γ": "\\\\Gamma ", "Δ": "\\\\Delta ", "Θ": "\\\\Theta ", "Λ": "\\\\Lambda ", "Ξ": "\\\\Xi ",
    "Π": "\\\\Pi ", "Σ": "\\\\Sigma ", "Υ": "\\\\Upsilon ", "Φ": "\\\\Phi ", "Ψ": "\\\\Psi ", "Ω": "\\\\Omega ",
    "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
    "⁺": "^+", "⁻": "^-", "⁼": "^=", "⁽": "^(", "⁾": "^)", "ⁿ": "^n", "ⁱ": "^i",
    "₀": "_0", "₁": "_1", "₂": "_2", "₃": "_3", "₄": "_4", "₅": "_5", "₆": "_6", "₇": "_7", "₈": "_8", "₉": "_9",
    "₊": "_+", "₋": "_-", "₌": "_=", "₍": "_(", "₎": "_)",
    "ₐ": "_a", "ₑ": "_e", "ₒ": "_o", "ₓ": "_x", "ₕ": "_h", "ₖ": "_k", "ₗ": "_l", "ₘ": "_m", "ₙ": "_n", "ₚ": "_p", "ₛ": "_s", "ₜ": "_t",
    "′": "'", "″": "''", "‰": "\\\\permil ", "°": "^\\\\circ ", "℃": "^\\\\circ\\\\text{C}",
    "ℓ": "\\\\ell ", "ℕ": "\\\\mathbb{N}", "ℤ": "\\\\mathbb{Z}", "ℚ": "\\\\mathbb{Q}", "ℝ": "\\\\mathbb{R}", "ℂ": "\\\\mathbb{C}",
}


def replace_unicode_math(text: str) -> tuple[str, int]:
    count = 0
    for symbol, replacement in UNICODE_REPLACEMENTS.items():
        if symbol in text:
            occurrences = text.count(symbol)
            text = text.replace(symbol, replacement)
            count += occurrences
    return text, count


# === 自动包裹数学表达式 ===

_MATH_SPAN_RE = re.compile(
    r"(?s)"
    r"(?<!\\)\$\$.*?(?<!\\)\$\$"
    r"|(?<!\\)\$.*?(?<!\\)\$"
    r"|\\\(.+?\\\)"
    r"|\\\[.+?\\\]"
)

_INLINE_DOLLAR_RE = re.compile(r"(?s)(?<!\\)\$.*?(?<!\\)\$")

_POINT_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"(?:[A-Z])"
    r"\(\s*[A-Za-z0-9_+\-*/^]+"
    r"(?:\s*[,，]\s*[A-Za-z0-9_+\-*/^]+)+"
    r"\s*\)"
)

_POINT_SUBSCRIPT_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z]{1,4}_(?:[0-9]{1,3}|[A-Za-z])"
    r"\(\s*[A-Za-z0-9_+\-*/^]+"
    r"(?:\s*[,，]\s*[A-Za-z0-9_+\-*/^]+)+"
    r"\s*\)"
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")

_OPTION_LABEL_RE = re.compile(r"(?<![A-Za-z0-9_])([A-D])\.")
_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>]*")

_PAREN_CHUNK = r"\([^()]*\)"

_PAREN_RELATION_RE = re.compile(
    r"\(\s*"
    r"([A-Za-z0-9][A-Za-z0-9_+\-*/^(),.\s]*?"
    r"(?:<=|>=|=|<|>|≤|≥|≠)"
    r"\s*[A-Za-z0-9.][A-Za-z0-9_+\-*/^(),.\s]*?)"
    r"\s*\)"
)

_CHAIN_RELATION_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"(?:[A-Za-z][A-Za-z0-9_+\-*/^().]*|[0-9]+[A-Za-z_][A-Za-z0-9_+\-*/^().]*)"
    r"(?:\s*(?:<=|>=|=|<|>|≤|≥|≠)\s*[A-Za-z0-9_+\-*/^().]+){3,}"
)

_RELATION_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"(?:[A-Za-z](?:(?:[A-Za-z0-9_+\-*/^().\s]|" + _PAREN_CHUNK + r"))*?|"
    r"[0-9]+[A-Za-z_](?:(?:[A-Za-z0-9_+\-*/^().\s]|" + _PAREN_CHUNK + r"))*?)"
    r"\s*(?:<=|>=|=|<|>|≤|≥|≠)\s*"
    r"[A-Za-z0-9.]"
    r"(?:"
    r"(?:(?:[A-Za-z0-9_+\-*/^().]|" + _PAREN_CHUNK + r")|(?:\s+(?!\()))*"
    r"[A-Za-z0-9.)]"
    r")?"
    r"(?=(?:\s+\()|\s*\(|\s*[,，]|\s*[^A-Za-z0-9_+\-*/^().\s]|\s*$)"
)

_MATH_FUNC_NAMES = {"log", "ln", "lg", "sin", "cos", "tan", "cot", "sec", "csc", 
                    "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
                    "exp", "lim", "max", "min", "sup", "inf", "det", "dim", "ker", "gcd"}

_MATH_COMMAND_NAMES = "|".join(sorted(_MATH_FUNC_NAMES, key=len, reverse=True))

_LATEX_COMMAND_RE = re.compile(
    rf"\\(?:{_MATH_COMMAND_NAMES})"
    r"(?:_(?:\{[^{}]*\}|[A-Za-z0-9]+))?"
    r"(?:\s*\{[^{}]*\}|\s*\([^\)]*\)|\s+[A-Za-z0-9_]+)"
)

_LATEX_COMMAND_EXPR_RE = re.compile(
    rf"(?:\\(?:{_MATH_COMMAND_NAMES})"
    r"(?:_(?:\{[^{}]*\}|[A-Za-z0-9]+))?"
    r"(?:\s*\{[^{}]*\}|\s*\([^\)]*\)|\s+[A-Za-z0-9_]+))"
    r"(?:\s*[\+\-\*/]\s*"
    rf"(?:\\(?:{_MATH_COMMAND_NAMES})"
    r"(?:_(?:\{[^{}]*\}|[A-Za-z0-9]+))?"
    r"(?:\s*\{[^{}]*\}|\s*\([^\)]*\)|\s+[A-Za-z0-9_]+)))*"
)

_FUNC_NAME_CALL_RE = re.compile(
    rf"(?<![A-Za-z0-9_\\])(?:{_MATH_COMMAND_NAMES})\s*\([^\)]*\)"
)

_FUNC_CALL_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z]"
    r"\([A-Za-z0-9_+\-*/^,\s]+\)"
)

_LATEX_SQRT_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"(?:[0-9]+)?"
    r"\\sqrt"
    r"(?:\s*\{[^{}]*\}|\s+[A-Za-z0-9]+|[0-9]+)"
)

_LATEX_TRIANGLE_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"\\triangle"
    r"(?:\s*\{[A-Z]{1,3}\}|\s*[A-Z]{1,3})?"
)

_LATEX_SYMBOL_COMMANDS = {
    # Greek (lowercase + variants)
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi",
    "varpi", "rho", "varrho", "sigma", "varsigma", "tau", "upsilon", "phi",
    "varphi", "chi", "psi", "omega",
    # Greek (uppercase)
    "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Upsilon",
    "Phi", "Psi", "Omega",
    # Common operators/relations/arrows
    "pm", "mp", "times", "div", "cdot", "sum", "prod", "int", "iint", "iiint", "infty",
    "le", "leq", "ge", "geq", "ne", "neq", "approx", "equiv", "propto", "ll", "gg",
    "in", "notin", "ni", "subset", "supset", "subseteq", "supseteq", "cup", "cap", "emptyset",
    "land", "lor", "neg", "forall", "exists", "nexists",
    "to", "rightarrow", "leftarrow", "leftrightarrow", "Rightarrow", "Leftarrow", "Leftrightarrow",
    "uparrow", "downarrow", "nearrow", "searrow", "swarrow", "nwarrow",
    "Longrightarrow", "Longleftarrow", "Longleftrightarrow",
    # Geometry and set/shape symbols
    "angle", "perp", "parallel", "nparallel", "sim", "cong", "frown",
    "circ", "bigcirc", "bullet", "square", "blacksquare", "diamond", "blacklozenge",
    "odot", "oplus", "otimes", "nabla", "ell",
}

_LATEX_SYMBOL_COMMAND_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"\\(?:"
    + "|".join(sorted(_LATEX_SYMBOL_COMMANDS, key=len, reverse=True))
    + r")"
    r"(?![A-Za-z])"
    r"(?:"
    r"(?:_(?:\{[^{}]*\}|[A-Za-z0-9]+))|"
    r"(?:\^(?:\{[^{}]*\}|[A-Za-z0-9]+))"
    r")*"
)

_LETTER_DIGIT_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z]"
    r"[0-9]{1,3}"
    r"(?![A-Za-z0-9_]|\\.[0-9])"
)

_TRIANGLE_NOTATION_RE = re.compile(
    r"(?:Rt△|△|三角形)\s*([A-Z]{3})"
)

_SUBSCRIPT_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z]{1,4}"
    r"_(?:[0-9]{1,3}|[A-Za-z])"
    r"(?![A-Za-z0-9_])"
)

_DIFFERENTIAL_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"(?:d[^\s/]+|d[A-Za-z])"
    r"/"
    r"(?:d[^\s/]+|d[A-Za-z])"
    r"(?![A-Za-z0-9_])"
)

_SEQUENCE_INDEX_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"([aA]|S)"
    r"([0-9]{1,3})"
    r"(?![A-Za-z0-9_])"
)

_PRIME_FUNC_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z]'+\s*\([A-Za-z0-9_+\-*/^,\s]*\)"
)

_PRIME_VAR_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z]'+"
    r"(?![A-Za-z0-9_])"
)

_VERSION_RE = re.compile(r"\b[vV]\d+(?:\.\d+)+\b|\b[vV]\d+\b")

_FRACTION_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[0-9]+/[A-Za-z]"
    r"(?![A-Za-z0-9_])"
)

_POWER_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"[A-Za-z](?:[A-Za-z0-9_]*\s*\^\s*[A-Za-z0-9]+)"
    r"(?![A-Za-z0-9_])"
)

_MERGE_REL_BOTH_RE = re.compile(
    r"\$([^$]+)\$\s*(<=|>=|=|<|>|≤|≥|≠)\s*\$([^$]+)\$"
)

_MERGE_REL_RIGHT_RE = re.compile(
    r"\$([^$]+)\$\s*(<=|>=|=|<|>|≤|≥|≠)\s*(?!\()([A-Za-z0-9_+\-*/^().]+)"
)

_SIMPLE_REL_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"([A-Za-z])\s*(<=|>=|=|<|>|≤|≥|≠)\s*([A-Za-z0-9]+)"
)

_MERGE_REL_SPLIT_RE = re.compile(
    r"\$([A-Za-z])\$\s*(<=|>=|=|<|>|≤|≥|≠)\s*([A-Za-z0-9]+)\$"
)
_SINGLE_LETTER_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])"
    r"([A-Za-z])"
    r"(?![A-Za-z0-9_])"
)

_UNICODE_MATH_OPS = "∩∪⊥∥·×÷±∓≤≥≠≈≡∝≪≫∈∉∋⊂⊃⊆⊇→←↔⇒⇐⇔"
_UNICODE_MATH_TOKEN = r"(?:[A-Za-z]+|[0-9]+(?:\.[0-9]+)?)"
_UNICODE_MATH_OP_RE = re.compile(
    r"(?<![A-Za-z0-9_\\$])"
    r"(?:"
    + _UNICODE_MATH_TOKEN
    + r"(?:\s*[" + re.escape(_UNICODE_MATH_OPS) + r"]\s*" + _UNICODE_MATH_TOKEN + r")+)"
)


def _merge_adjacent_display_math(text: str) -> str:
    pattern = re.compile(r"\$\$([^$]+)\$\$\s*([+\-*/])\s*\$\$([^$]+)\$\$")
    while True:
        new_text, n = pattern.subn(r"$$\1\2\3$$", text)
        if n == 0:
            return text
        text = new_text


def _split_by_spans(text: str, spans: list[tuple[int, int]]) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    last = 0
    for s, e in spans:
        if s > last:
            out.append((False, text[last:s]))
        out.append((True, text[s:e]))
        last = e
    if last < len(text):
        out.append((False, text[last:]))
    return out


def _apply_outside_inline_math(segment: str, regex: re.Pattern, wrap_fn) -> tuple[str, int]:
    spans = [(m.start(), m.end()) for m in _INLINE_DOLLAR_RE.finditer(segment)]
    parts = _split_by_spans(segment, spans)
    wraps = 0
    new_parts: list[str] = []
    for is_math, part in parts:
        if is_math:
            new_parts.append(part)
            continue
        def repl(m: re.Match) -> str:
            nonlocal wraps
            wraps += 1
            return wrap_fn(m)
        new_parts.append(regex.sub(repl, part))
    return "".join(new_parts), wraps


def wrap_math_expressions(text: str) -> tuple[str, int]:
    """识别文本中的数学表达式并用 $...$ 包裹。
    
    识别：下标变量(l_1)、等式/不等式(y^2=2px, p>0)、坐标点(M(4,0))、单字母变量(F,C)。
    """
    spans = [(m.start(), m.end()) for m in _MATH_SPAN_RE.finditer(text)]
    chunks = _split_by_spans(text, spans)
    total_wraps = 0
    out_chunks: list[str] = []

    for is_math, chunk in chunks:
        if is_math:
            out_chunks.append(chunk)
            continue

        s = chunk
        version_tokens: list[tuple[str, str]] = []
        path_tokens: list[tuple[str, str]] = []
        html_tokens: list[tuple[str, str]] = []
        option_tokens: list[tuple[str, str]] = []

        def _protect_paths(segment: str) -> str:
            def repl(m: re.Match) -> str:
                token = f"##PATH{len(path_tokens)}##"
                path_tokens.append((token, m.group(0)))
                return token
            return _PATH_RE.sub(repl, segment)

        def _protect_versions(segment: str) -> str:
            def repl(m: re.Match) -> str:
                token = f"%%{len(version_tokens)}%%"
                version_tokens.append((token, m.group(0)))
                return token
            return _VERSION_RE.sub(repl, segment)

        def _protect_html_tags(segment: str) -> str:
            def repl(m: re.Match) -> str:
                token = f"@@{len(html_tokens)}@@"
                html_tokens.append((token, m.group(0)))
                return token
            return _HTML_TAG_RE.sub(repl, segment)

        def _protect_option_labels(segment: str) -> str:
            def repl(m: re.Match) -> str:
                token = f"||{len(option_tokens)}||"
                option_tokens.append((token, m.group(0)))
                return token
            return _OPTION_LABEL_RE.sub(repl, segment)

        def _restore_versions(segment: str) -> str:
            for token, original in version_tokens:
                segment = segment.replace(token, original)
            return segment

        def _restore_paths(segment: str) -> str:
            for token, original in path_tokens:
                segment = segment.replace(token, original)
            return segment

        def _restore_html_tags(segment: str) -> str:
            for token, original in html_tokens:
                segment = segment.replace(token, original)
            return segment

        def _restore_option_labels(segment: str) -> str:
            for token, original in option_tokens:
                segment = segment.replace(token, original)
            return segment

        s = _protect_paths(s)
        s = _protect_versions(s)
        s = _protect_html_tags(s)
        s = _protect_option_labels(s)
        s = _SEQUENCE_INDEX_RE.sub(lambda m: f"{m.group(1)}_{m.group(2)}", s)

        def _wrap_nested_calls(segment: str) -> str:
            out: list[str] = []
            i = 0
            length = len(segment)
            skip_names = {
                "if", "for", "while", "switch", "case", "catch", "return", "def", "class"
            }
            while i < length:
                ch = segment[i]
                if ch.isascii() and ch.isalpha() and (i == 0 or not (segment[i - 1].isalnum() or segment[i - 1] in "_\\")):
                    j = i
                    while j < length and segment[j].isascii() and segment[j].isalpha():
                        j += 1
                    name = segment[i:j].lower()
                    k = j
                    while k < length and segment[k].isspace():
                        k += 1
                    if k < length and segment[k] == "(":
                        if name in skip_names:
                            out.append(segment[i:k])
                            i = k
                            continue
                        depth = 0
                        m = k
                        while m < length:
                            if segment[m] == "(":
                                depth += 1
                            elif segment[m] == ")":
                                depth -= 1
                                if depth == 0:
                                    break
                            m += 1
                        if depth == 0 and m < length:
                            out.append(f"${segment[i:m + 1]}$")
                            i = m + 1
                            continue
                out.append(ch)
                i += 1
            return "".join(out)

        s = _wrap_nested_calls(s)

        def _normalize_relation_spacing(expr: str) -> str:
            expr = re.sub(r"\s*(<=|>=|=|<|>|≤|≥|≠)\s*", r" \1 ", expr)
            return re.sub(r"\s+", " ", expr).strip()

        def _wrap_paren_relation(m: re.Match) -> str:
            return f"(${_normalize_relation_spacing(m.group(1))}$)"
        s, c = _apply_outside_inline_math(s, _PAREN_RELATION_RE, _wrap_paren_relation)
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _CHAIN_RELATION_RE, lambda m: f"${_normalize_relation_spacing(m.group(0))}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _RELATION_RE, lambda m: f"${_normalize_relation_spacing(m.group(0))}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _LATEX_COMMAND_EXPR_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _LATEX_SQRT_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _LATEX_TRIANGLE_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _LATEX_SYMBOL_COMMAND_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _FUNC_NAME_CALL_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _FUNC_CALL_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _FRACTION_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _POINT_SUBSCRIPT_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _POINT_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _DIFFERENTIAL_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        def _wrap_triangle(m: re.Match) -> str:
            prefix = m.group(0)[: -len(m.group(1))]
            return f"{prefix}${m.group(1)}$"

        s, c = _apply_outside_inline_math(s, _TRIANGLE_NOTATION_RE, _wrap_triangle)
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _PRIME_FUNC_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _PRIME_VAR_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _POWER_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _UNICODE_MATH_OP_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        s, c = _apply_outside_inline_math(s, _LETTER_DIGIT_RE, lambda m: f"${m.group(0)}$")
        total_wraps += c

        def _wrap_subscript_if_not_func(m: re.Match) -> str:
            matched = m.group(0)
            base = matched.split("_")[0].lower()
            if base in _MATH_FUNC_NAMES:
                return matched
            return f"${matched}$"
        
        s, c = _apply_outside_inline_math(s, _SUBSCRIPT_RE, _wrap_subscript_if_not_func)
        total_wraps += c

        spans2 = [(m.start(), m.end()) for m in _INLINE_DOLLAR_RE.finditer(s)]
        parts2 = _split_by_spans(s, spans2)
        rebuilt: list[str] = []

        for is_math2, part in parts2:
            if is_math2:
                rebuilt.append(part)
                continue

            def repl_single(m: re.Match) -> str:
                nonlocal total_wraps
                i0, i1 = m.start(1), m.end(1)
                prev_ch = part[i0 - 1] if i0 - 1 >= 0 else ""
                next_ch = part[i1] if i1 < len(part) else ""
                chinese = ("\u4e00" <= prev_ch <= "\u9fff") or ("\u4e00" <= next_ch <= "\u9fff")
                punct = (prev_ch == "" or prev_ch.isspace() or prev_ch in "，。,:：;；()（）[]【】<>《》\"\"\"'、~-") or \
                        (next_ch == "" or next_ch.isspace() or next_ch in "，。,:：;；()（）[]【】<>《》\"\"\"'、~-")
                if not (chinese or punct):
                    return m.group(1)
                total_wraps += 1
                return f"${m.group(1)}$"

            rebuilt.append(_SINGLE_LETTER_RE.sub(repl_single, part))

        s = _restore_versions("".join(rebuilt))
        s = _restore_option_labels(s)
        s = _MERGE_REL_BOTH_RE.sub(
            lambda m: f"${_normalize_relation_spacing(m.group(1) + m.group(2) + m.group(3))}$",
            s,
        )
        s = _MERGE_REL_RIGHT_RE.sub(
            lambda m: f"${_normalize_relation_spacing(m.group(1) + m.group(2) + m.group(3))}$",
            s,
        )
        s, _ = _apply_outside_inline_math(s, _SIMPLE_REL_RE, lambda m: f"${m.group(1)}{m.group(2)}{m.group(3)}$")
        s = _MERGE_REL_SPLIT_RE.sub(lambda m: f"${m.group(1)}{m.group(2)}{m.group(3)}$", s)
        s = _restore_html_tags(s)
        s = re.sub(r"<[^>]*>", lambda m: m.group(0).replace("$", ""), s)
        s = re.sub(r"\$([^$<]+)</", r"$\1$</", s)
        s = re.sub(r"\$([^$()]*)\)\$", r"$\1$)", s)
        s = re.sub(r"\$([^$()]*?)(\){2,})\$", r"$\1$\2", s)
        s = re.sub(r"\$([^$]+?)\s+(且|或|并)", r"$\1$ \2", s)
        s = re.sub(r"\$([^$]+?)\$\s*/in\s*\$([^$]+?)\$", r"$\1 /in \2$", s)
        s, _ = _apply_outside_inline_math(s, _SIMPLE_REL_RE, lambda m: f"${m.group(1)}{m.group(2)}{m.group(3)}$")
        s = _MERGE_REL_SPLIT_RE.sub(lambda m: f"${m.group(1)}{m.group(2)}{m.group(3)}$", s)
        s = _restore_paths(s)
        out_chunks.append(s)

    result = "".join(out_chunks)
    result = _merge_adjacent_display_math(result)
    return result, total_wraps


def _check_unicode_math_symbols(s: str, path: str, line: int | None = None, col: int | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    found = []
    first_pos: int | None = None
    for symbol, latex in UNICODE_MATH_SYMBOLS.items():
        idx = s.find(symbol)
        if idx != -1:
            found.append(f"{symbol} → {latex}")
            if first_pos is None or idx < first_pos:
                first_pos = idx
    if found:
        sample = "、".join(found[:5])
        if len(found) > 5:
            sample += f" 等共 {len(found)} 个"
        adjusted_col = (col + first_pos) if col is not None and first_pos is not None else col
        issues.append(
            ValidationIssue(
                severity="warning",
                path=path,
                line=line,
                col=adjusted_col,
                message=f"检测到 Unicode 数学符号（建议改用 LaTeX 命令）：{sample}",
            )
        )
    return issues


def _get_all_math_ranges(scan: dict) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    double_starts = scan["double_dollars"]
    for i in range(0, len(double_starts) - 1, 2):
        ranges.append((double_starts[i], double_starts[i + 1] + 2))
    double_positions = {pos for start in double_starts for pos in (start, start + 1)}
    single_dollars = [pos for pos in scan["unescaped_dollars"] if pos not in double_positions]
    for i in range(0, len(single_dollars) - 1, 2):
        ranges.append((single_dollars[i], single_dollars[i + 1] + 1))
    ranges.extend(scan["inline_math_ranges"])
    ranges.extend(scan["display_math_ranges"])
    ranges.sort(key=lambda x: x[0])
    return ranges


def _find_unescaped_outside_math(s: str, ch: str, math_ranges: list[tuple[int, int]]) -> int | None:
    if ch != "_":
        i = 0
        while i < len(s):
            if s[i] == ch:
                backslash_count = 0
                j = i - 1
                while j >= 0 and s[j] == "\\":
                    backslash_count += 1
                    j -= 1
                if backslash_count % 2 == 0:
                    in_math = any(start <= i < end for start, end in math_ranges)
                    if not in_math:
                        return i
            i += 1
        return None

    skip_patterns = [
        re.compile(r"__BLANK__"),
        re.compile(r"!\[.*?\]\([^)]*_[^)]*\)"),
        re.compile(r"[a-zA-Z]:/[^\s\"]*_[^\s\"]*"),
        re.compile(r"/[^\s\"]*_[^\s\"]*"),
        re.compile(r"\\includegraphics[^{]*\{[^}]*_[^}]*\}"),
        re.compile(r"\\input\{[^}]*_[^}]*\}"),
    ]
    skip_ranges: list[tuple[int, int]] = []
    for pat in skip_patterns:
        for m in pat.finditer(s):
            skip_ranges.append((m.start(), m.end()))

    i = 0
    while i < len(s):
        if s[i] == "_":
            backslash_count = 0
            j = i - 1
            while j >= 0 and s[j] == "\\":
                backslash_count += 1
                j -= 1
            if backslash_count % 2 == 0:
                in_math = any(start <= i < end for start, end in math_ranges)
                in_skip = any(start <= i < end for start, end in skip_ranges)
                if not in_math and not in_skip:
                    return i
        i += 1
    return None


def _strip_math_segments(s: str) -> str:
    scan = _scan_latex_structure(s)
    ranges: list[tuple[int, int]] = []

    double_starts = scan["double_dollars"]
    for i in range(0, len(double_starts) - 1, 2):
        start = double_starts[i]
        end = double_starts[i + 1] + 2
        ranges.append((start, end))

    double_positions = {pos for start in double_starts for pos in (start, start + 1)}
    single_dollars = [pos for pos in scan["unescaped_dollars"] if pos not in double_positions]
    for i in range(0, len(single_dollars) - 1, 2):
        start = single_dollars[i]
        end = single_dollars[i + 1] + 1
        ranges.append((start, end))

    ranges.extend(scan["inline_math_ranges"])
    ranges.extend(scan["display_math_ranges"])

    if not ranges:
        return s

    ranges.sort(key=lambda item: item[0])
    out: list[str] = []
    last = 0
    for start, end in ranges:
        if end <= start:
            continue
        if start < last:
            start = last
        if start > last:
            out.append(s[last:start])
        last = max(last, min(end, len(s)))
    out.append(s[last:])
    return "".join(out)


def _check_env_balance(s: str, path: str, line: int | None = None, col: int | None = None) -> list[ValidationIssue]:
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
                issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message=f"检测到 \\end{{{name}}} 但缺少对应的 \\begin"))
                continue
            top = stack.pop()
            if top != name:
                issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message=f"环境不匹配：\\begin{{{top}}} ... \\end{{{name}}}"))

    for name in reversed(stack):
        issues.append(ValidationIssue(severity="warning", path=path, line=line, col=col, message=f"检测到 \\begin{{{name}}} 但缺少对应的 \\end"))

    return issues


class _StringLocator:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.line_starts = [0]
        for i, ch in enumerate(raw):
            if ch == "\n":
                self.line_starts.append(i + 1)

    def locate(self, path: str, value: str) -> tuple[int | None, int | None]:
        idx = self._find_best_match(path, value)
        if idx is None:
            return None, None
        line = bisect.bisect_right(self.line_starts, idx)
        col = idx - self.line_starts[line - 1] + 1
        return line, col

    def _find_best_match(self, path: str, value: str) -> int | None:
        literals = self._candidate_literals(value)
        occurrences: list[int] = []
        for lit in literals:
            start = 0
            while True:
                idx = self.raw.find(lit, start)
                if idx == -1:
                    break
                occurrences.append(idx)
                start = idx + len(lit)

        if not occurrences:
            return None
        if len(occurrences) == 1:
            return occurrences[0]

        key = self._extract_last_key(path)
        if key:
            key_token = f"\"{key}\""
            key_positions: list[int] = []
            start = 0
            while True:
                kidx = self.raw.find(key_token, start)
                if kidx == -1:
                    break
                key_positions.append(kidx)
                start = kidx + len(key_token)

            for kidx in key_positions:
                for lit in literals:
                    idx = self.raw.find(lit, kidx)
                    if idx != -1:
                        return idx

        return occurrences[0]

    def _candidate_literals(self, value: str) -> list[str]:
        literals = []
        dumped = json.dumps(value, ensure_ascii=False)
        literals.append(dumped)
        dumped_ascii = json.dumps(value, ensure_ascii=True)
        if dumped_ascii != dumped:
            literals.append(dumped_ascii)
        return literals

    def _extract_last_key(self, path: str) -> str | None:
        if not path:
            return None
        parts = path.split(".")
        for part in reversed(parts):
            key = part.split("[", 1)[0]
            if key:
                return key
        return None
