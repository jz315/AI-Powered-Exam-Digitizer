"""Sophisticated edge-case tests from Oracle."""
import json
import pytest
from math_digitizer.core.validator import (
    _scan_latex_structure,
    _strip_verbatim,
    validate_json_and_latex,
)


def _wrap_content(content: str) -> str:
    payload = {
        "meta": {"title": "T", "subject": "S"},
        "sections": [{"type": "problem", "questions": [{"content": content}]}],
    }
    return json.dumps(payload, ensure_ascii=False)


class TestSophisticatedBackslashCases:
    def test_five_backslashes_then_dollar_is_escaped(self):
        scan = _scan_latex_structure(r"\\\\\$x$")
        assert len(scan["unescaped_dollars"]) == 1

    def test_six_backslashes_then_dollar_is_unescaped(self):
        scan = _scan_latex_structure(r"\\\\\\$x$")
        assert len(scan["unescaped_dollars"]) == 2

    def test_trailing_backslash_does_not_crash(self):
        scan = _scan_latex_structure("ends with backslash \\")
        assert scan["comment_ranges"] == []
        assert scan["unescaped_dollars"] == []

    def test_trailing_backslash_in_content_stable(self):
        json_str = _wrap_content("ends with backslash \\")
        _, issues = validate_json_and_latex(json_str)
        assert not any(i.severity == "error" for i in issues)


class TestNestedStructures:
    def test_math_inside_environment_underscore_ok(self):
        json_str = _wrap_content(r"\begin{center}$x_1$\end{center}")
        _, issues = validate_json_and_latex(json_str)
        assert not any("未转义的 _" in i.message for i in issues)

    def test_environment_inside_math_no_false_warnings(self):
        json_str = _wrap_content(r"$\begin{matrix}1&2\\3&4\end{matrix}$")
        _, issues = validate_json_and_latex(json_str)
        assert not any("环境不匹配" in i.message for i in issues)
        assert not any("未转义的 &" in i.message for i in issues)

    def test_comment_hides_unbalanced_dollar(self):
        json_str = _wrap_content(r"$x$ % $this_should_be_ignored")
        _, issues = validate_json_and_latex(json_str)
        assert not any("未成对的 $" in i.message for i in issues)

    def test_verbatim_hides_fake_environment_tokens(self):
        json_str = _wrap_content(r"\begin{verbatim}\begin{align}x\end{align}\end{verbatim}")
        _, issues = validate_json_and_latex(json_str)
        assert not any("环境不匹配" in i.message for i in issues)


class TestJSONEscapeDetection:
    def test_json_newline_escape_flagged(self):
        json_str = (
            '{"meta":{"title":"T","subject":"S"},'
            '"sections":[{"type":"problem","questions":[{"content":"line1\\nline2"}]}]}'
        )
        _, issues = validate_json_and_latex(json_str)
        assert any(i.severity == "error" and "\\n 转义" in i.message for i in issues)

    def test_json_literal_backslash_n_warned(self):
        json_str = (
            '{"meta":{"title":"T","subject":"S"},'
            '"sections":[{"type":"problem","questions":[{"content":"\\\\n."}]}]}'
        )
        _, issues = validate_json_and_latex(json_str)
        assert any(i.severity == "warning" and "字面量 \\n" in i.message for i in issues)

    def test_begin_control_escape_detected(self):
        json_str = (
            '{"meta":{"title":"T","subject":"S"},'
            '"sections":[{"type":"problem","questions":[{"content":"\\frac{1}{2}"}]}]}'
        )
        _, issues = validate_json_and_latex(json_str)
        ctrl_issues = [i for i in issues if "控制字符" in i.message]
        assert len(ctrl_issues) > 0


class TestBoundaryConditions:
    def test_empty_content_ok(self):
        json_str = _wrap_content("")
        _, issues = validate_json_and_latex(json_str)
        assert not any(i.severity == "error" for i in issues)

    def test_single_dollar_error(self):
        json_str = _wrap_content("$")
        _, issues = validate_json_and_latex(json_str)
        assert any(i.severity == "error" and "未成对的 $" in i.message for i in issues)

    def test_extremely_long_string_stable(self):
        content = ("a" * 50000) + " $x$ " + ("b" * 50000)
        json_str = _wrap_content(content)
        _, issues = validate_json_and_latex(json_str)
        assert not any(i.severity == "error" for i in issues)


class TestKnownLimitations:
    @pytest.mark.xfail(reason="Known: _strip_verbatim doesn't handle minted with options")
    def test_minted_with_options_stripped(self):
        s = r"text \begin{minted}[linenos]{python}x_1\end{minted} more"
        stripped = _strip_verbatim(s)
        assert "x_1" not in stripped

    @pytest.mark.xfail(reason=r"Known: only \verb|...| stripped, not \verb+...+")
    def test_verb_non_pipe_delimiter_stripped(self):
        json_str = _wrap_content(r"prefix \verb+$%&_+ suffix")
        _, issues = validate_json_and_latex(json_str)
        assert not any("未转义的" in i.message for i in issues)


class TestUnicodeMathSymbolDetection:
    def test_times_symbol_warning(self):
        json_str = _wrap_content("3×4=12")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "×" in unicode_issues[0].message

    def test_sqrt_symbol_warning(self):
        json_str = _wrap_content("√9=3")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0

    def test_greek_pi_warning(self):
        json_str = _wrap_content("周长=2πr")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "π" in unicode_issues[0].message

    def test_multiple_unicode_symbols(self):
        json_str = _wrap_content("a≤b≤c 且 x∈A∪B")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0

    def test_latex_command_no_warning(self):
        json_str = _wrap_content("$3 \\times 4 = 12$")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) == 0

    def test_infinity_symbol_warning(self):
        json_str = _wrap_content("极限趋向∞")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "∞" in unicode_issues[0].message

    def test_arrows_warning(self):
        json_str = _wrap_content("A→B⇒C")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0

    def test_triangle_symbol_warning(self):
        json_str = _wrap_content("设O为坐标原点,若△ABF的面积为83")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "△" in unicode_issues[0].message

    def test_subscript_number_warning(self):
        json_str = _wrap_content("直线l₂与y轴交于点N")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "₂" in unicode_issues[0].message

    def test_angle_symbol_warning(self):
        json_str = _wrap_content("∠ABC=90°")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "∠" in unicode_issues[0].message

    def test_parallel_perpendicular_warning(self):
        json_str = _wrap_content("若AB⊥CD且EF∥GH")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0

    def test_superscript_number_warning(self):
        json_str = _wrap_content("x²+y³=z")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
        assert "²" in unicode_issues[0].message

    def test_congruent_similar_warning(self):
        json_str = _wrap_content("△ABC≌△DEF,且△GHI∽△JKL")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0

    def test_mathbb_sets_warning(self):
        json_str = _wrap_content("x∈ℝ,n∈ℕ,z∈ℂ")
        _, issues = validate_json_and_latex(json_str)
        unicode_issues = [i for i in issues if "Unicode 数学符号" in i.message]
        assert len(unicode_issues) > 0
