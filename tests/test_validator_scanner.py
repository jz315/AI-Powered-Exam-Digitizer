"""Tests for validator scanner fixes."""
import json
from math_digitizer.core.validator import (
    validate_json_and_latex,
    _scan_latex_structure,
    _strip_comments,
    _strip_verbatim,
    _strip_math_segments,
)


class TestBackslashAwareScanner:
    """Test odd/even backslash detection for $ and braces."""

    def test_basic_dollar_pair(self):
        s = "$x$"
        scan = _scan_latex_structure(s)
        assert len(scan["unescaped_dollars"]) == 2

    def test_escaped_dollar_single_backslash(self):
        s = r"\$100"
        scan = _scan_latex_structure(s)
        assert len(scan["unescaped_dollars"]) == 0

    def test_double_backslash_then_dollar(self):
        s = r"\\$x$"
        scan = _scan_latex_structure(s)
        assert len(scan["unescaped_dollars"]) == 2

    def test_triple_backslash_escaped_dollar(self):
        s = r"\\\$"
        scan = _scan_latex_structure(s)
        assert len(scan["unescaped_dollars"]) == 0

    def test_quad_backslash_unescaped_dollar(self):
        s = r"\\\\$x$"
        scan = _scan_latex_structure(s)
        assert len(scan["unescaped_dollars"]) == 2

    def test_double_dollar(self):
        s = "$$x$$"
        scan = _scan_latex_structure(s)
        assert len(scan["double_dollars"]) == 2
        assert len(scan["unescaped_dollars"]) == 4

    def test_escaped_braces(self):
        s = r"{x} and \{y\}"
        scan = _scan_latex_structure(s)
        assert len(scan["unescaped_open_braces"]) == 1
        assert len(scan["unescaped_close_braces"]) == 1


class TestCommentStripping:
    def test_strip_single_comment(self):
        s = "text % comment"
        result = _strip_comments(s)
        assert result == "text "

    def test_strip_comment_preserves_newline(self):
        s = "text % comment\nmore"
        result = _strip_comments(s)
        assert result == "text \nmore"

    def test_escaped_percent(self):
        s = r"100\% complete"
        result = _strip_comments(s)
        assert result == s


class TestVerbatimStripping:
    def test_strip_verbatim_env(self):
        s = r"text \begin{verbatim}$%&\end{verbatim} more"
        result = _strip_verbatim(s)
        assert "$" not in result
        assert "text" in result
        assert "more" in result

    def test_strip_verb_command(self):
        s = r"text \verb|$%&| more"
        result = _strip_verbatim(s)
        assert "$" not in result


class TestMathStripping:
    def test_strip_inline_math(self):
        s = "text $x_1$ more"
        result = _strip_math_segments(s)
        assert "x_1" not in result
        assert "text" in result
        assert "more" in result

    def test_strip_display_math(self):
        s = r"text \[x^2\] more"
        result = _strip_math_segments(s)
        assert "x^2" not in result


class TestJSONValidation:
    def test_reject_nan(self):
        result, issues = validate_json_and_latex('{"a": NaN}')
        assert result is None
        assert any(i.severity == "error" for i in issues)

    def test_reject_infinity(self):
        result, issues = validate_json_and_latex('{"a": Infinity}')
        assert result is None
        assert any(i.severity == "error" for i in issues)

    def test_valid_json(self):
        result, issues = validate_json_and_latex(
            '{"meta": {"title": "Test", "subject": "Math"}, "sections": []}'
        )
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0
        assert result is not None


class TestEnvBalance:
    def test_balanced_env(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\begin{align}x\\\\end{align}"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        env_issues = [i for i in issues if "begin" in i.message.lower() or "end" in i.message.lower()]
        assert len(env_issues) == 0

    def test_unbalanced_env(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\begin{align}x\\\\end{equation}"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        env_issues = [i for i in issues if "环境不匹配" in i.message or "mismatch" in i.message.lower()]
        assert len(env_issues) > 0


class TestLeftRightOrder:
    def test_correct_left_right_order(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\left(x\\\\right)"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        order_issues = [i for i in issues if "right" in i.message.lower() and "之前" in i.message]
        assert len(order_issues) == 0

    def test_wrong_left_right_order(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\right)x\\\\left("}]}]}'
        result, issues = validate_json_and_latex(json_str)
        order_issues = [i for i in issues if "之前" in i.message]
        assert len(order_issues) > 0

    def test_nested_left_right(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\left(\\\\left[x\\\\right]\\\\right)"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        lr_issues = [i for i in issues if "left" in i.message.lower() or "right" in i.message.lower()]
        assert len(lr_issues) == 0


class TestInlineDisplayMathPairing:
    def test_balanced_inline_math(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\(x+1\\\\)"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        paren_issues = [i for i in issues if "\\\\(" in i.message or "\\\\)" in i.message]
        assert len(paren_issues) == 0

    def test_unbalanced_inline_math(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\(x+1"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        paren_issues = [i for i in issues if "\\(" in i.message and "\\)" in i.message]
        assert len(paren_issues) > 0

    def test_balanced_display_math(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\[x^2\\\\]"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        bracket_issues = [i for i in issues if "\\\\[" in i.message or "\\\\]" in i.message]
        assert len(bracket_issues) == 0

    def test_unbalanced_display_math(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\[x^2"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        bracket_issues = [i for i in issues if "\\[" in i.message and "\\]" in i.message]
        assert len(bracket_issues) > 0


class TestDollarPairing:
    def test_paired_dollars(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "$x$ and $y$"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        dollar_issues = [i for i in issues if "未成对的 $" in i.message]
        assert len(dollar_issues) == 0

    def test_unpaired_dollar(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "$x and y"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        dollar_issues = [i for i in issues if "未成对的 $" in i.message]
        assert len(dollar_issues) > 0

    def test_escaped_dollar_not_counted(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\$100 is $x$"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        dollar_issues = [i for i in issues if "未成对的 $" in i.message]
        assert len(dollar_issues) == 0

    def test_double_dollar_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "$$x^2$$"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        dd_issues = [i for i in issues if "$$" in i.message]
        assert len(dd_issues) > 0


class TestBraceBalance:
    def test_balanced_braces(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "{a}{b}{c}"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        brace_issues = [i for i in issues if "{ }" in i.message]
        assert len(brace_issues) == 0

    def test_unbalanced_braces(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "{a}{b{c}"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        brace_issues = [i for i in issues if "{ }" in i.message]
        assert len(brace_issues) > 0

    def test_escaped_braces_not_counted(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\{a\\\\}"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        brace_issues = [i for i in issues if "{ }" in i.message]
        assert len(brace_issues) == 0


class TestUnescapedSpecialChars:
    def test_unescaped_percent_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "50\\\\% off"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        pct_issues = [i for i in issues if "%" in i.message and "未转义" in i.message]
        assert len(pct_issues) == 0

    def test_escaped_percent_no_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "50\\\\% off"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        pct_issues = [i for i in issues if "%" in i.message and "未转义" in i.message]
        assert len(pct_issues) == 0

    def test_unescaped_ampersand_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "A & B"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        amp_issues = [i for i in issues if "&" in i.message and "未转义" in i.message]
        assert len(amp_issues) > 0

    def test_underscore_in_math_no_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "$x_1$"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        underscore_issues = [i for i in issues if "_" in i.message and "未转义" in i.message]
        assert len(underscore_issues) == 0

    def test_underscore_outside_math_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "var_name"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        underscore_issues = [i for i in issues if "_" in i.message and "未转义" in i.message]
        assert len(underscore_issues) > 0


class TestSchemaValidation:
    def test_missing_sections(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}}'
        result, issues = validate_json_and_latex(json_str)
        section_issues = [i for i in issues if "sections" in i.message]
        assert len(section_issues) > 0

    def test_missing_meta_warning(self):
        json_str = '{"sections": []}'
        result, issues = validate_json_and_latex(json_str)
        meta_issues = [i for i in issues if "meta" in i.path]
        assert len(meta_issues) > 0

    def test_invalid_section_type_warning(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "unknown", "questions": []}]}'
        result, issues = validate_json_and_latex(json_str)
        type_issues = [i for i in issues if "type" in i.path]
        assert len(type_issues) > 0

    def test_choice_question_missing_options(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "single_choice", "questions": [{"content": "Q1"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        opt_issues = [i for i in issues if "options" in i.message]
        assert len(opt_issues) > 0

    def test_valid_choice_question(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "single_choice", "questions": [{"content": "Q1", "options": ["A", "B"]}]}]}'
        result, issues = validate_json_and_latex(json_str)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


class TestEmptyAndEdgeCases:
    def test_empty_string(self):
        result, issues = validate_json_and_latex("")
        assert result is None
        assert len(issues) == 0

    def test_invalid_json_syntax(self):
        result, issues = validate_json_and_latex("{invalid}")
        assert result is None
        assert any(i.severity == "error" for i in issues)

    def test_json_array_not_object(self):
        result, issues = validate_json_and_latex("[]")
        assert any("对象" in i.message for i in issues)

    def test_deeply_nested_structure(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "Q", "sub": {"deep": {"value": "$x$"}}}]}]}'
        result, issues = validate_json_and_latex(json_str)
        assert result is not None


class TestControlCharacterDetection:
    def test_control_char_from_bad_escape(self):
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\frac"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        ctrl_issues = [i for i in issues if "控制字符" in i.message]
        assert len(ctrl_issues) > 0


class TestCommentHandling:
    def test_comment_content_not_validated(self):
        scan = _scan_latex_structure("text % $unbalanced")
        assert scan["comment_ranges"] == [(5, 18)]

    def test_multiple_comments(self):
        s = "a % c1\nb % c2\nc"
        result = _strip_comments(s)
        assert result == "a \nb \nc"


class TestVerbatimHandling:
    def test_lstlisting_stripped(self):
        s = r"text \begin{lstlisting}$code$\end{lstlisting} more"
        result = _strip_verbatim(s)
        assert "$code$" not in result

    def test_minted_stripped(self):
        s = r"text \begin{minted}{python}x_1\end{minted} more"
        result = _strip_verbatim(s)
        assert "x_1" not in result


class TestMathSegmentStripping:
    def test_mixed_math_modes(self):
        s = r"a $b$ c \(d\) e \[f\] g"
        result = _strip_math_segments(s)
        assert "b" not in result
        assert "d" not in result
        assert "f" not in result
        assert "a" in result
        assert "c" in result
        assert "e" in result
        assert "g" in result

    def test_double_dollar_stripped(self):
        s = "a $$b^2$$ c"
        result = _strip_math_segments(s)
        assert "b^2" not in result
        assert "a" in result
        assert "c" in result


class TestScannerEdgeCases:
    def test_odd_backslashes_escape_percent_comment(self):
        # Odd backslashes should escape %, avoiding comment strip.
        scan = _scan_latex_structure(r"\\\% not a comment")
        assert scan["comment_ranges"] == []

    def test_even_backslashes_allow_comment(self):
        # Even backslashes mean % starts a comment.
        scan = _scan_latex_structure(r"\\% comment")
        assert scan["comment_ranges"] == [(2, 11)]

    def test_backslash_run_resets_on_text(self):
        # Backslash run should reset after non-backslash characters.
        scan = _scan_latex_structure(r"\\a$1$")
        assert len(scan["unescaped_dollars"]) == 2

    def test_odd_backslashes_escape_dollar(self):
        # Odd backslash run should escape the dollar.
        scan = _scan_latex_structure(r"\\\\\$")
        assert len(scan["unescaped_dollars"]) == 0


class TestRegexEdgeCases:
    def test_strip_verbatim_two_blocks(self):
        # Non-greedy regex should remove each block separately.
        s = r"a \\begin{verbatim}1\\end{verbatim} b \\begin{verbatim}2\\end{verbatim} c"
        result = _strip_verbatim(s)
        assert "1" not in result
        assert "2" not in result
        assert "a" in result
        assert "c" in result

    def test_strip_verbatim_missing_end(self):
        # Missing \end should not consume the rest of the string.
        s = r"start \\begin{verbatim}$x"
        result = _strip_verbatim(s)
        assert "$x" in result

    def test_strip_verb_unclosed_delimiter(self):
        # Unclosed \verb should remain unchanged.
        s = r"text \\verb|no end"
        result = _strip_verbatim(s)
        assert result == s


class TestInterleavedDelimiters:
    def test_interleaved_dollar_inline_math_strip(self):
        # Overlapping $...$ and \( ... \) should not break stripping.
        s = r"text $a \\(b$ c\\) tail"
        result = _strip_math_segments(s)
        assert "$a" not in result
        assert "\\(b" not in result
        assert "text" in result
        assert "tail" in result

    def test_interleaved_dollar_causes_unpaired_error(self):
        # Interleaving with a missing closing $ should still be detected.
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "$x \\\\(y\\\\)"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        dollar_issues = [i for i in issues if "未成对的 $" in i.message]
        assert len(dollar_issues) > 0


class TestMalformedLatexInputs:
    def test_end_without_begin_warning(self):
        # Real user mistake: stray \end without \begin.
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\end{align}"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        env_issues = [i for i in issues if "\\\\end" in i.message or "缺少对应的 \\begin" in i.message]
        assert len(env_issues) > 0

    def test_begin_missing_end_warning(self):
        # Missing \end is common in pasted LaTeX snippets.
        json_str = '{"meta": {"title": "T", "subject": "S"}, "sections": [{"type": "problem", "questions": [{"content": "\\\\begin{align}x"}]}]}'
        result, issues = validate_json_and_latex(json_str)
        env_issues = [i for i in issues if "缺少对应的 \\end" in i.message]
        assert len(env_issues) > 0


class TestUnicodeMathSymbols:
    def test_unicode_times_symbol_no_control_char(self):
        # Unicode symbols should not trip control-character detection.
        payload = {
            "meta": {"title": "T", "subject": "S"},
            "sections": [{"type": "problem", "questions": [{"content": "面积=3×4"}]}],
        }
        json_str = json.dumps(payload, ensure_ascii=False)
        result, issues = validate_json_and_latex(json_str)
        ctrl_issues = [i for i in issues if "控制字符" in i.message]
        assert len(ctrl_issues) == 0

    def test_unicode_sqrt_symbol_no_control_char(self):
        # Unicode symbols should not trip control-character detection.
        payload = {
            "meta": {"title": "T", "subject": "S"},
            "sections": [{"type": "problem", "questions": [{"content": "√9=3"}]}],
        }
        json_str = json.dumps(payload, ensure_ascii=False)
        result, issues = validate_json_and_latex(json_str)
        ctrl_issues = [i for i in issues if "控制字符" in i.message]
        assert len(ctrl_issues) == 0
