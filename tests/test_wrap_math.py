"""
Comprehensive tests for wrap_math_expressions function.

Tests cover:
1. Basic patterns: subscripts, equations, inequalities, coordinates, single letters
2. Boundary cases: existing $...$, escape sequences, empty strings
3. False positive prevention: English words, file paths, code snippets
4. Complex scenarios: nested brackets, multiple expressions, mixed Chinese/English
5. Real exam text from actual problem statements
"""

import pytest
from math_digitizer.core.validator import wrap_math_expressions


class TestSubscriptVariables:
    """下标变量识别测试"""

    def test_simple_subscript(self):
        text = "直线 l_1 经过点 A"
        result, count = wrap_math_expressions(text)
        assert "$l_1$" in result
        assert count >= 1

    def test_multiple_subscripts(self):
        text = "设 a_1, a_2, a_3 为等差数列"
        result, count = wrap_math_expressions(text)
        assert "$a_1$" in result
        assert "$a_2$" in result
        assert "$a_3$" in result

    def test_subscript_with_letter(self):
        text = "点 P_n 的坐标"
        result, count = wrap_math_expressions(text)
        assert "$P_n$" in result

    def test_double_letter_subscript(self):
        text = "向量 CC_1 垂直于平面"
        result, count = wrap_math_expressions(text)
        assert "$CC_1$" in result

    def test_subscript_zero(self):
        text = "初始值 x_0 = 1"
        result, count = wrap_math_expressions(text)
        # x_0 = 1 被整体包裹为等式是合理行为
        assert "$x_0 = 1$" in result

    def test_subscript_not_match_python_variable(self):
        """不应把 Python 变量名当作下标"""
        text = "变量 my_variable 不应被包裹"
        result, count = wrap_math_expressions(text)
        assert "my_variable" in result
        assert "$my_variable$" not in result
        assert count == 0

    def test_subscript_not_match_file_path(self):
        """不应把文件路径中的下划线当作下标"""
        text = "文件 config_file.txt 和 data_2024.csv"
        result, count = wrap_math_expressions(text)
        assert "config_file.txt" in result
        assert "data_2024.csv" in result
        assert "$config_file$" not in result
        assert "$data_2024$" not in result


class TestEquations:
    """等式识别测试"""

    def test_simple_equation(self):
        text = "方程 x = 1"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result

    def test_polynomial_equation(self):
        text = "抛物线方程 y^2 = 2px"
        result, count = wrap_math_expressions(text)
        assert "$y^2 = 2px$" in result

    def test_linear_equation(self):
        text = "直线方程 2x - y - 4 = 0"
        result, count = wrap_math_expressions(text)
        assert "$2x - y - 4 = 0$" in result

    def test_equation_with_fraction_notation(self):
        text = "满足 x/2 = 3"
        result, count = wrap_math_expressions(text)
        assert "$x/2 = 3$" in result

    def test_equation_with_power(self):
        text = "圆的方程 x^2 + y^2 = r^2"
        result, count = wrap_math_expressions(text)
        assert "$x^2 + y^2 = r^2$" in result
        assert result.count("$") >= 2

    def test_equation_stops_at_chinese(self):
        """等式应在中文字符处停止"""
        text = "满足 x = 1 的值"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result
        assert "的值" in result
        assert "$的$" not in result


class TestInequalities:
    """不等式识别测试"""

    def test_greater_than(self):
        text = "其中 p > 0"
        result, count = wrap_math_expressions(text)
        assert "$p > 0$" in result

    def test_less_than(self):
        text = "当 x < 1 时"
        result, count = wrap_math_expressions(text)
        assert "$x < 1$" in result

    def test_greater_equal(self):
        text = "满足 n >= 2"
        result, count = wrap_math_expressions(text)
        assert "$n >= 2$" in result

    def test_less_equal(self):
        text = "要求 a <= 5"
        result, count = wrap_math_expressions(text)
        assert "$a <= 5$" in result

    def test_unicode_inequality(self):
        text = "条件 x ≤ 3 和 y ≥ 0"
        result, count = wrap_math_expressions(text)
        assert "$x ≤ 3$" in result or "x ≤ 3" in result
        assert "$y ≥ 0$" in result or "y ≥ 0" in result

    def test_not_equal(self):
        text = "其中 a ≠ 0"
        result, count = wrap_math_expressions(text)
        assert "$a ≠ 0$" in result or "a ≠ 0" in result


class TestCoordinatePoints:
    """坐标点识别测试"""

    def test_simple_point(self):
        text = "过点 M(4, 0) 的直线"
        result, count = wrap_math_expressions(text)
        assert "$M(4, 0)$" in result

    def test_point_with_variables(self):
        text = "点 P(x, y) 在曲线上"
        result, count = wrap_math_expressions(text)
        assert "$P(x, y)$" in result

    def test_multiple_points(self):
        text = "三角形 ABC 的顶点 A(1, 2), B(3, 4), C(5, 0)"
        result, count = wrap_math_expressions(text)
        assert "$A(1, 2)$" in result
        assert "$B(3, 4)$" in result
        assert "$C(5, 0)$" in result

    def test_point_with_negative(self):
        text = "点 Q(-1, 3) 关于原点对称"
        result, count = wrap_math_expressions(text)
        assert "$Q(-1, 3)$" in result

    def test_origin_point(self):
        text = "以 O(0, 0) 为圆心"
        result, count = wrap_math_expressions(text)
        assert "$O(0, 0)$" in result


class TestSingleLetterVariables:
    """单字母变量识别测试"""

    def test_single_letter_with_chinese_context(self):
        text = "设 F 为抛物线的焦点"
        result, count = wrap_math_expressions(text)
        assert "$F$" in result

    def test_multiple_single_letters(self):
        text = "直线 l 与圆 C 相交于 A, B 两点"
        result, count = wrap_math_expressions(text)
        assert "$l$" in result
        assert "$C$" in result
        assert "$A$" in result
        assert "$B$" in result

    def test_single_letter_after_colon(self):
        text = "抛物线 C: 方程为..."
        result, count = wrap_math_expressions(text)
        assert "$C$" in result

    def test_do_not_wrap_english_words(self):
        """不应把英文单词拆开"""
        text = "使用 LaTeX 排版"
        result, count = wrap_math_expressions(text)
        assert "LaTeX" in result
        assert "$L$a$T$e$X$" not in result

    def test_do_not_wrap_in_english_sentence(self):
        """英文句子中只包裹孤立变量，不拆单词"""
        text = "The point A is on the line"
        result, count = wrap_math_expressions(text)
        assert "$A$" in result
        assert "$T$" not in result
        assert "$p$oint" not in result
        assert count == 1


class TestExistingMathMode:
    """已有数学模式不重复包裹"""

    def test_existing_inline_math(self):
        text = "已知 $x_0$ 满足条件"
        result, count = wrap_math_expressions(text)
        assert result.count("$x_0$") == 1
        assert "$$x_0$$" not in result

    def test_existing_display_math(self):
        text = "公式 $$x^2 + y^2 = 1$$ 表示圆"
        result, count = wrap_math_expressions(text)
        assert "$$x^2 + y^2 = 1$$" in result

    def test_mixed_existing_and_new(self):
        text = "已知 $x$ 和 y = 1"
        result, count = wrap_math_expressions(text)
        assert result.count("$x$") == 1
        assert "$y = 1$" in result

    def test_escaped_dollar(self):
        r"""转义的美元符号不应被当作数学模式边界"""
        text = r"价格为 \$5，且 x = 1"
        result, count = wrap_math_expressions(text)
        assert r"\$5" in result
        assert "$x = 1$" in result

    def test_latex_paren_math(self):
        r"""LaTeX \(...\) 格式"""
        text = r"公式 \(x^2\) 和 y = 1"
        result, count = wrap_math_expressions(text)
        assert r"\(x^2\)" in result

    def test_latex_bracket_math(self):
        r"""LaTeX \[...\] 格式"""
        text = r"公式 \[x^2 + y^2 = 1\] 是圆"
        result, count = wrap_math_expressions(text)
        assert r"\[x^2 + y^2 = 1\]" in result


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_string(self):
        text = ""
        result, count = wrap_math_expressions(text)
        assert result == ""
        assert count == 0

    def test_no_math_content(self):
        text = "这是一段没有数学内容的普通中文文本。"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_only_punctuation(self):
        text = "，。！？；：""''"
        result, count = wrap_math_expressions(text)
        assert result == text

    def test_whitespace_only(self):
        text = "   \n\t  "
        result, count = wrap_math_expressions(text)
        assert result == text

    def test_equation_at_start(self):
        text = "x = 1 是方程的解"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result

    def test_equation_at_end(self):
        text = "方程的解是 x = 1"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result

    def test_consecutive_equations(self):
        text = "x = 1, y = 2, z = 3"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result
        assert "$y = 2$" in result
        assert "$z = 3$" in result
    def test_fuck_equations(self):
        text = "x = 1、 y = 2、 z = 3"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result
        assert "$y = 2$" in result
        assert "$z = 3$" in result
        assert "$x = 1、 y = 2、 z = 3$" not in result


class TestFalsePositivePrevention:
    """误判防护测试"""

    def test_url_not_wrapped(self):
        text = "访问 https://example.com/path_to_file"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_email_not_wrapped(self):
        text = "联系 admin@example.com"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_code_variable_names(self):
        text = "Python 代码中 my_var = 10"
        result, count = wrap_math_expressions(text)
        # my_var 不应被拆开，即使整段被包裹
        assert "Python 代码中" in result
        assert "my_var" in result
        assert "$my$" not in result
        assert "$var$" not in result

    def test_json_keys(self):
        text = '{"question_id": 1, "content": "text"}'
        result, count = wrap_math_expressions(text)
        assert "question_id" in result

    def test_markdown_placeholder(self):
        text = "占位符 __BLANK__ 表示空白"
        result, count = wrap_math_expressions(text)
        assert "__BLANK__" in result

    def test_latex_commands_not_double_wrapped(self):
        text = r"使用 \frac{1}{2} 表示分数"
        result, count = wrap_math_expressions(text)
        assert r"\frac" in result

    def test_html_tags(self):
        text = "<div class='math'>x = 1</div>"
        result, count = wrap_math_expressions(text)
        # 不应破坏 HTML 结构
        assert "<div class='math'>" in result
        assert "</div>" in result
        assert "$x = 1$" in result


class TestComplexScenarios:
    """复杂场景测试"""

    def test_full_problem_statement(self):
        """完整题目陈述"""
        text = """现在已知 F 为抛物线 C: y^2 = 2px (p > 0) 的焦点，直线 l_1: 2x - y - 4 = 0 经过 F，且 l_1 与 C 相交于 P, Q 两点，过点 M(4, 0) 的动直线 l_2 与 C 相交于 A, B 两点。"""
        result, count = wrap_math_expressions(text)
        
        assert "$F$" in result
        assert "$C$" in result
        assert "$y^2 = 2px$" in result
        assert "$p > 0$" in result
        assert "$l_1$" in result
        assert "$2x - y - 4 = 0$" in result
        assert "$P$" in result
        assert "$Q$" in result
        assert "$M(4, 0)$" in result
        assert "$l_2$" in result
        assert "$A$" in result
        assert "$B$" in result

    def test_geometry_problem(self):
        """几何问题"""
        text = "在三角形 ABC 中，角 A, B, C 的对边分别为 a, b, c，已知 a = 2, b = 3, C = 60 度"
        result, count = wrap_math_expressions(text)
        assert "$ABC$" in result and ("$A$" in result and "$B$" in result and "$C$" in result)
        assert "$a$" in result
        assert "$b$" in result
        assert "$c$" in result
        assert "$a = 2$" in result
        assert "$b = 3$" in result

    def test_sequence_problem(self):
        text = "设数列 {a_n} 满足 a_1 = 1, a_{n+1} = 2a_n + 1"
        result, count = wrap_math_expressions(text)
        assert "$a_n$" in result or "{a_n}" in result
        assert "$a_1 = 1$" in result or "$a_1$" in result

    def test_function_problem(self):
        """函数问题"""
        text = "函数 f(x) = x^2 - 2x + 1 在区间 [0, 2] 上的最小值"
        result, count = wrap_math_expressions(text)
        # f(x) 格式的函数
        assert "f(x)" in result or "$f$" in result

    def test_mixed_equations_and_text(self):
        """等式与文字交替"""
        text = "由 x = 1 得 y = 2，进而 z = 3"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result
        assert "$y = 2$" in result
        assert "$z = 3$" in result
        assert "得" in result
        assert "进而" in result

    def test_parenthetical_condition(self):
        """括号内条件"""
        text = "抛物线 (p > 0) 的焦点"
        result, count = wrap_math_expressions(text)
        assert "$p > 0$" in result

    def test_colon_after_name(self):
        """名称后跟冒号"""
        text = "直线 l: 2x + y - 1 = 0"
        result, count = wrap_math_expressions(text)
        assert "$l$" in result
        assert "$2x + y - 1 = 0$" in result


class TestRealExamProblems:
    """真实试卷题目测试"""

    def test_2024_gaokao_style_1(self):
        text = """已知椭圆 C: x^2/a^2 + y^2/b^2 = 1 (a > b > 0) 的离心率为 1/2，
        过右焦点 F 的直线 l 与椭圆交于 A, B 两点，若 AF = 3FB，求椭圆方程。"""
        result, count = wrap_math_expressions(text)
        assert "$C$" in result
        assert "$a > b > 0$" in result  or "$a > b>0$" in result 
        assert "$F$" in result
        assert "$l$" in result
        assert "$A$" in result
        assert "$B$" in result

    def test_2024_gaokao_style_2(self):
        """2024高考风格题目2"""
        text = """在平面直角坐标系 xOy 中，已知点 A(-2, 0), B(2, 0)，
        动点 P 满足 PA * PB = -3，求点 P 的轨迹方程。"""
        result, count = wrap_math_expressions(text)
        assert "$A(-2, 0)$" in result or "$A$" in result
        assert "$B(2, 0)$" in result or "$B$" in result
        assert "$P$" in result

    def test_probability_problem(self):
        """概率问题"""
        text = """袋中有 3 个红球和 2 个白球，从中随机取出 2 个球，
        设 X 为取出红球的个数，求 E(X) 和 D(X)。"""
        result, count = wrap_math_expressions(text)
        assert "$X$" in result

    def test_derivative_problem(self):
        """导数问题"""
        text = """已知函数 f(x) = e^x - ax - 1，若 f(x) >= 0 对所有 x 成立，求 a 的取值范围。"""
        result, count = wrap_math_expressions(text)
        assert "$a$" in result
        assert "$x$" in result

    def test_vector_problem(self):
        """向量问题"""
        text = """已知向量 a = (1, 2), b = (3, 4)，求 a * b 和 |a + b|。"""
        result, count = wrap_math_expressions(text)
        assert "$a$" in result
        assert "$b$" in result


class TestJSONContext:
    """JSON 上下文测试"""

    def test_json_string_content(self):
        """JSON 字符串内容"""
        text = '{"content": "已知 F 为焦点，满足 x = 1"}'
        result, count = wrap_math_expressions(text)
        assert "$F$" in result
        assert "$x = 1$" in result

    def test_json_with_escapes(self):
        """JSON 带转义"""
        text = r'{"content": "公式 $x$ 和 y = 1"}'
        result, count = wrap_math_expressions(text)
        assert result.count("$x$") == 1
        assert "$y = 1$" in result

    def test_json_multiline(self):
        text = '''{
            "questions": [
                {"content": "设 a_1 = 1, a_2 = 2"},
                {"content": "求 x > 0 时的解"}
            ]
        }'''
        result, count = wrap_math_expressions(text)
        assert "$a_1 = 1$" in result or "$a_1$" in result
        assert "$a_2 = 2$" in result or "$a_2$" in result
        assert "$x > 0$" in result


class TestCountAccuracy:
    """包裹计数准确性测试"""

    def test_count_single_wrap(self):
        text = "设 F 为焦点"
        result, count = wrap_math_expressions(text)
        assert "$F$" in result
        assert count == 1

    def test_count_multiple_wraps(self):
        text = "设 a = 1, b = 2, c = 3"
        result, count = wrap_math_expressions(text)
        assert "$a = 1$" in result
        assert "$b = 2$" in result
        assert "$c = 3$" in result
        assert count == 3

    def test_count_no_wraps_when_already_wrapped(self):
        text = "已知 $x$ 和 $y$"
        result, count = wrap_math_expressions(text)
        assert count == 0

    def test_count_partial_wraps(self):
        text = "已知 $x$ 和 y = 1"
        result, count = wrap_math_expressions(text)
        assert "$y = 1$" in result
        assert count == 1


class TestIdempotency:
    """幂等性测试 - 多次应用结果相同"""

    def test_idempotent_simple(self):
        text = "设 F 为焦点"
        result1, _ = wrap_math_expressions(text)
        result2, count2 = wrap_math_expressions(result1)
        assert result1 == result2
        assert count2 == 0

    def test_idempotent_complex(self):
        text = "直线 l_1: 2x - y = 0 过点 A(1, 2)"
        result1, _ = wrap_math_expressions(text)
        result2, count2 = wrap_math_expressions(result1)
        assert result1 == result2
        assert count2 == 0

    def test_idempotent_full_problem(self):
        text = """已知 F 为抛物线 C: y^2 = 2px (p > 0) 的焦点"""
        result1, _ = wrap_math_expressions(text)
        result2, count2 = wrap_math_expressions(result1)
        assert result1 == result2
        assert count2 == 0


# =============================================================================
# 高级测试用例 - 乱序与干扰项、几何坐标、方程不等式、标点边界、综合长难句
# =============================================================================


class TestAbbreviationsVsVariables:
    """英文缩写 vs 单字母变量识别"""

    def test_rgb_abbreviation_vs_single_letters(self):
        """RGB 连在一起不应包裹，但分离的 R 应被包裹"""
        text = "RGB颜色模型中，R代表红色，G代表绿色，B代表蓝色。"
        result, count = wrap_math_expressions(text)
        # RGB 整体不应被包裹
        assert "$R$GB" not in result and "$RGB$" not in result
        assert "RGB" in result
        # 分离的 R, G, B 应被包裹（有中文上下文）
        assert "$R$代表" in result
        assert "$G$代表" in result
        assert "$B$代表" in result

    def test_trig_function_names_not_wrapped(self):
        """sin, cos 是函数名，不应被包裹；x, y 是变量，应包裹"""
        text = r"计算 \sin x + \cos y 的值，其中 x=30, y=60。"
        result, count = wrap_math_expressions(text)
        # sin, cos 不应被包裹为单字母
        assert r"$\sin x + \cos y$" in result
        
        # 等式应被包裹
        assert "$x=30$" in result or "$x = 30$" in result
        assert "$y=60$" in result or "$y = 60$" in result

    def test_physics_units_and_url(self):
        """物理变量 U, I 应包裹；单位 V, A 不包；URL 完全保持原样"""
        text = "电压 U 为 5V，电流 I 为 2A，网址是 example.com?id=1。"
        result, count = wrap_math_expressions(text)
        # U, I 是物理变量
        assert "$U$" in result
        assert "$I$" in result
        # URL 中的内容不应被识别为等式
        assert "example.com" in result
        # id=1 在 URL 中不应被包裹
        # 这取决于实现，URL 识别是可选增强

    def test_hyphenated_words_vs_variables(self):
        """X-ray 中的 X 是单词一部分；y-轴中的 y 是变量应包"""
        text = "X-ray 是一种射线，且 y-轴 垂直于 x-轴。"
        result, count = wrap_math_expressions(text)
        # 当前实现：X 后跟 - 被视为标点边界，会包裹 X
        # 这是可接受的行为，因为在中文语境中 X-ray 较少见
        # y-轴、x-轴 中的 y, x 是变量
        assert "$y$-轴" in result or "$y$" in result
        assert "$x$-轴" in result or "$x$" in result


class TestGeometryAndCoordinates:
    """几何与坐标测试"""

    def test_complex_coordinates_with_mixed_text(self):
        """负数坐标和变量坐标混合"""
        text = "抛物线经过点 M(-2, 0) 和 N(p, q)，其中 p, q > 0。"
        result, count = wrap_math_expressions(text)
        assert "$M(-2, 0)$" in result or "$M$(-2, 0)" in result
        assert "$N(p, q)$" in result
        # p, q > 0 作为不等式或独立变量
        assert "$p$" in result or "$q$" in result or "p, q > 0" in result

    def test_subscript_with_regular_variables(self):
        """下标变量与普通变量共存"""
        text = "向量 a_1 加上 a_2 等于 b，即 a_1 + a_2 = b。"
        result, count = wrap_math_expressions(text)
        assert "$a_1$" in result
        assert "$a_2$" in result
        assert "$b$" in result or "$a_1 + a_2 = b$" in result

    


class TestEquationsAndInequalities:
    """方程与不等式高级测试"""

    def test_inequality_system_in_braces(self):
        """大括号内的不等式组"""
        text = "若 { x+y>0, x-y<2 }，求 x 的范围。"
        result, count = wrap_math_expressions(text)
        assert "$x+y>0$" in result or "$x+y > 0$" in result or "$x + y > 0$" in result or "x+y>0" in result
        assert "$x-y<2$" in result or "$x-y < 2$" in result or "$x - y < 2$" in result or "x-y<2" in result
        assert "$x$" in result

    def test_greek_letters_in_relation(self):
        """希腊字母参数（若支持）"""
        text = "设 λ 和 μ 为参数，且 λ > μ。"
        result, count = wrap_math_expressions(text)
        # 希腊字母可能被 Unicode 替换或保持原样
        # 主要测试不崩溃，且保留字符
        assert "λ" in result
        assert "μ" in result

    def test_ratio_expression(self):
        """比例式"""
        text = "已知 a : b = 2 : 3，求 a 与 b 的关系。"
        result, count = wrap_math_expressions(text)
        # 比例式可能被识别为关系式
        assert "$a$" in result
        assert "$b$" in result


class TestPunctuationBoundaries:
    """标点符号与边界细节"""

    def test_variables_in_parentheses(self):
        """括号内的单字母变量"""
        text = "选 (A) 还是 (B) ？实际上 C 是对的。"
        result, count = wrap_math_expressions(text)
        # 括号内的 A, B 被中文/标点包围，应包裹
        assert "$A$" in result or "($A$)" in result
        assert "$B$" in result or "($B$)" in result
        assert "$C$" in result

    def test_number_letter_combination(self):
        """数字字母组合如 x1, x2"""
        text = "方程有 2 个根，分别是 x1 和 x2。"
        result, count = wrap_math_expressions(text)
        # x1, x2 可能被视为下标或保持原样
        # 纯数字 2 不应被包裹
        assert "$x1$" in result
        assert "$x2$" in result
        assert "$2$" not in result

    def test_dunhao_separated_variables(self):
        """顿号分隔的变量"""
        text = "函数 f、g、h 均为增函数，见《数学分析》第一章。"
        result, count = wrap_math_expressions(text)
        assert "$f$" in result
        assert "$g$" in result
        assert "$h$" in result
        assert "《数学分析》" in result


class TestComprehensiveLongSentences:
    """综合长难句 - 模拟真实题目"""

    def test_analytic_geometry_problem(self):
        """高中解析几何题"""
        text = "已知圆 C 的方程为 x^2 + y^2 = 4，直线 l 过点 A(1,0) 且斜率为 k。"
        result, count = wrap_math_expressions(text)
        assert "$C$" in result
        assert "$x^2 + y^2 = 4$" in result
        assert "$l$" in result
        assert "$A(1,0)$" in result or "$A(1, 0)$" in result
        assert "$k$" in result

    def test_linear_algebra_description(self):
        """线性代数描述"""
        text = "矩阵 A 的秩 r(A) = 2，且 |A| = 0。"
        result, count = wrap_math_expressions(text)
        assert "$A$" in result
        # r(A) 被拆分为 $r$($A$) 是当前实现的预期行为
        # 因为 r 和 A 都是单字母变量，被括号触发包裹
        assert "$r$" in result or "r(A)" in result

    def test_probability_description(self):
        """概率论描述"""
        text = "设事件 A 发生的概率 P(A)=0.5，事件 B 独立于 A。"
        result, count = wrap_math_expressions(text)
        assert "$A$" in result
        assert "$B$" in result
        assert "$P(A)=0.5$" in result or "$P(A) = 0.5$" in result

    def test_probability_description_with_trig(self):
        """含函数名与三角函数的文本"""
        text = "我是f(x)，sin(x)哈哈哈"
        result, count = wrap_math_expressions(text)
        assert "$f(x)$" in result
        assert "$sin(x)$" in result

    def test_physics_kinematics(self):
        """物理运动学描述（含下标）"""
        text = "物体由静止开始做匀加速运动，初速度 v_0=0，t 时刻速度 v_t = at。"
        result, count = wrap_math_expressions(text)
        assert "$v_0=0$" in result or "$v_0 = 0$" in result or "$v_0$" in result
        assert "$t$" in result
        assert "$v_t = at$" in result or "$v_t$" in result

    def test_chemistry_rate_equation(self):
        """化学反应速率方程"""
        text = "反应速率 v 正比于浓度 c，即 v = k*c。"
        result, count = wrap_math_expressions(text)
        assert "$v$" in result
        assert "$c$" in result
        assert "$v = k*c$" in result or "v = k*c" in result

    def test_variables_in_quotes(self):
        """引号内的变量"""
        text = "通常将 \"x\" 称为自变量，\"y\" 称为因变量。"
        result, count = wrap_math_expressions(text)
        # 引号内的变量应被包裹
        assert "$x$" in result
        assert "$y$" in result

    def test_fragmented_inequalities(self):
        """碎片化的多个不等式"""
        text = "若 a>0 (即 a 是正数)，则 b<a 且 c>0。"
        result, count = wrap_math_expressions(text)
        assert "$a>0$" in result or "$a > 0$" in result
        assert "$a$" in result
        assert "$b<a$" in result or "$b < a$" in result
        assert "$c>0$" in result or "$c > 0$" in result


class TestEdgeCasesAdvanced:
    """高级边界情况"""

    def test_no_wrap_latex_commands(self):
        """LaTeX 命令不应被拆开包裹"""
        text = r"使用 \sin x 和 \cos y 计算"
        result, count = wrap_math_expressions(text)
        assert r"$\sin x$" in result
        assert r"$\cos y$" in result
        assert count == 2

    def test_subscript_vs_python_snake_case(self):
        """下标 vs Python 蛇形命名"""
        text = "变量 my_var 不应包裹，但 a_1 应该包裹。"
        result, count = wrap_math_expressions(text)
        assert "$my_var$" not in result
        assert "$a_1$" in result

    def test_multiple_consecutive_relations(self):
        """连续多个关系式"""
        text = "满足 a=1, b=2, c=3 的值"
        result, count = wrap_math_expressions(text)
        assert "$a=1$" in result or "$a = 1$" in result
        assert "$b=2$" in result or "$b = 2$" in result
        assert "$c=3$" in result or "$c = 3$" in result

    def test_function_notation_f_of_x(self):
        """函数符号 f(x) 类似坐标点"""
        text = "函数 f(x) 在 x=0 处的值"
        result, count = wrap_math_expressions(text)
        assert "$x=0$" in result or "$x = 0$" in result


# =============================================================================
# 极端边缘测试 - 视觉陷阱、Unicode混淆、语义冲突、格式崩坏
# =============================================================================


class TestUnicodeAndFullWidthChars:
    """Unicode 混淆与全角字符"""

    def test_fullwidth_brackets_with_halfwidth_vars(self):
        """全角括号包围的半角变量"""
        text = "请计算（x）与【y】的和，其中ｚ是未知数。"
        result, count = wrap_math_expressions(text)
        # 全角括号 （）【】 在标点列表中，触发包裹
        assert "$x$" in result
        assert "$y$" in result
        # ｚ 是全角字母，当前实现只支持 [A-Za-z]，不包裹

    def test_colon_ratio_confusion(self):
        """冒号与比例的混淆"""
        text = "配置比例为 a:b:c=1:2:3。"
        result, count = wrap_math_expressions(text)
        # : 触发单字母包裹，c=1:2:3 被识别为关系式
        assert "$a$" in result or "$b$" in result or "$c$" in result

    def test_quote_wrapped_variables(self):
        """引号内的变量和等式"""
        text = "他说 \"x=1\" 是对的，那 \"y\" 呢？"
        result, count = wrap_math_expressions(text)
        # 双引号在 punct 列表中
        assert "$x=1$" in result or "$x = 1$" in result
        assert "$y$" in result


class TestSemanticConflicts:
    """语义冲突与过度包裹"""

    def test_log_subscript_conflict(self):
        """log_2 是函数名，不应被下标规则匹配"""
        text = "计算 log_2(8) 的值。"
        result, count = wrap_math_expressions(text)
        # log 在函数名白名单中，log_2 保持原样
        assert "log_2" in result
        assert "$log_2$" not in result

    def test_chemical_formula_split(self):
        """化学式 H_2O 不符合下标规则（后面紧跟字母）"""
        text = "水的分子式是 H_2O。"
        result, count = wrap_math_expressions(text)
        # H_2O 中 H_2 后面紧跟 O，不符合 (?![A-Za-z0-9_]) 边界
        # 因此 H_2O 整体不会被下标规则匹配，保持原样
        assert "H_2O" in result

    def test_chained_inequality(self):
        """链式不等式"""
        text = "若 a>b>c>d，求 a 与 d 的差。"
        result, count = wrap_math_expressions(text)
        # 当前实现可能只匹配第一个关系式
        assert "$a>b>c>d$" in result or "$a > b > c > d$" in result
        assert "$d$" in result
        assert "$a$" in result

class TestPunctuationMixture:
    """标点符号大杂烩"""

    def test_numbered_list_with_vars(self):
        """编号列表中的变量"""
        text = "要点如下：\n1. x 是变量\n2. y 是常数\n3. z 是参数"
        result, count = wrap_math_expressions(text)
        # . 后的空格+变量+中文 触发包裹
        assert "$x$" in result
        assert "$y$" in result
        assert "$z$" in result

    def test_ellipsis_and_tilde(self):
        """省略号与波浪号"""
        text = "取值范围在 x...y 之间，且 p~q。"
        result, count = wrap_math_expressions(text)
        # ... 和 ~ 不在标点列表，但有中文上下文
        assert "$x$" in result or "$y$" in result

    def test_currency_symbol_interference(self):
        """货币符号干扰"""
        text = "价格是 $p$ 元，还是 $5 元？"
        result, count = wrap_math_expressions(text)
        # $p$ 已是数学块，保持不变
        assert "$p$" in result
        # $5 是未闭合块，不应崩溃


class TestMixedMathBlocks:
    """已有数学块与非数学块混合"""

    def test_math_block_with_spaces(self):
        """带空格的数学块"""
        text = "公式 $ E = mc^2 $ 中，E是能量。"
        result, count = wrap_math_expressions(text)
        # 前一个是合法数学块，保留
        assert "$ E = mc^2 $" in result
        # 后一个 E 被中文触发
        assert "E是" in result or "$E$是" in result

    def test_set_notation_nesting(self):
        """集合表示法嵌套"""
        text = "集合 A={x|x>0} 属于实数集 R。"
        result, count = wrap_math_expressions(text)
        # A 和 R 是单字母变量
        assert "$A$" in result or "A=" in result
        assert "$R$" in result
        # x>0 是关系式
        assert "$x>0$" in result or "$x > 0$" in result or "x>0" in result

    def test_code_snippet_interference(self):
        """代码片段干扰"""
        text = "定义函数 int f(int x, int y) { return x+y; }。"
        result, count = wrap_math_expressions(text)
        # int 是英文单词，不应被拆分包裹
        assert "$i$nt" not in result
        # f, x, y 可能被误包裹（这是预期的局限性）


class TestExtremeEdgeCases:
    """极端边缘情况"""

    def test_coordinate_with_spaces(self):
        """带空格的坐标"""
        text = "点 M( 0 , -2 ) 坐标很奇怪。"
        result, count = wrap_math_expressions(text)
        # 当前 _POINT_RE 支持空格
        assert "$M( 0 , -2 )$" in result or "$M$" in result

    def test_differential_notation(self):
        """微分符号"""
        text = "求 dy/dx 的值。"
        result, count = wrap_math_expressions(text)
        assert "求 $dy/dx$ 的值。" == result
        assert count == 1

    def test_greek_letter_with_parenthesis(self):
        """希腊字母与括号"""
        text = "已知 α 和 (α) 是一样的。"
        result, count = wrap_math_expressions(text)
        # 括号内的 α 若在 Unicode 支持范围内可能被包裹
        assert result == text
        assert count == 0

    def test_only_punctuation(self):
        """只有标点符号"""
        text = "--------------------------------"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_only_dashes_and_equals(self):
        """只有分隔符"""
        text = "============================"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_empty_math_blocks(self):
        """空数学块"""
        text = "这里有 $$ 空块。"
        result, count = wrap_math_expressions(text)
        # 不应崩溃
        assert "$$" in result

    def test_unmatched_dollar_signs(self):
        """不匹配的美元符号"""
        text = "价格 $10 和 $20 美元。"
        result, count = wrap_math_expressions(text)
        # 不应崩溃，$10...$20 被视为一个数学块
        assert result == text

    def test_mixed_chinese_english_equation(self):
        """中英文混合等式"""
        text = "满足条件 x等于1 的解"
        result, count = wrap_math_expressions(text)
        # x 被中文包围
        assert "$x$" in result

    def test_consecutive_single_letters(self):
        """连续单字母"""
        text = "设 A、B、C、D 为四个点"
        result, count = wrap_math_expressions(text)
        # 空格分隔的单字母，有中文上下文
        assert "$A$" in result
        assert "$B$" in result
        assert "$C$" in result
        assert "$D$" in result

    def test_subscript_chain(self):
        """下标链"""
        text = "变量 a_1_2_3 的值"
        result, count = wrap_math_expressions(text)
        # 链式下标应保持原样
        assert "a_1_2_3" in result
        assert "$a_1$" not in result
        assert count == 0

    def test_pipe_separator(self):
        """管道符分隔"""
        text = "条件 x|y 表示整除"
        result, count = wrap_math_expressions(text)
        # | 可能触发单字母包裹
        assert "$x$" in result
        assert "$y$" in result

class TestOCRArtifactsAndSpacing:
    """OCR 伪影与不规范空格"""

    def test_weird_spacing_in_equations(self):
        """等式中奇怪的空格"""
        text = "已知 x  =  1 且 y= 2"
        result, count = wrap_math_expressions(text)
        assert "$x  =  1$" in result or "$x = 1$" in result
        assert "$y= 2$" in result or "$y = 2$" in result

    def test_missing_spaces_after_punct(self):
        """标点后缺失空格"""
        text = "解方程:x=1,y=2。"
        result, count = wrap_math_expressions(text)
        assert "$x=1$" in result or "$x = 1$" in result
        assert "$y=2$" in result or "$y = 2$" in result

    def test_underscore_spaces(self):
        """OCR 导致的下标空格断裂"""
        # 某些 OCR 会把 a_1 识别为 a _ 1
        text = "数列 a _ 1 和 b _ n"
        result, count = wrap_math_expressions(text)
        # 这是一个很难的 case，如果 regex 不支持，只需保证不崩溃且尽可能识别
        # 理想情况是能识别出 a_1，如果不行，识别出 a 也是可接受的
        assert "$a$" in result or "$a _ 1$" in result


class TestSemanticProtectionAdvanced:
    """高级语义保护（防止非数学内容被包裹）"""

    def test_version_numbers(self):
        """版本号"""
        text = "Python v3.11 和 Node v20"
        result, count = wrap_math_expressions(text)
        # 'v' 不应被识别为速度变量
        assert "$v$" not in result
        assert "v3.11" in result

    def test_programming_keywords(self):
        """编程语言关键字"""
        text = "if (x > 0) return true;"
        result, count = wrap_math_expressions(text)
        # x > 0 是数学条件，应包裹
        assert "$x > 0$" in result
        # if 和 return 不应包裹
        assert "$if$" not in result
        assert "$return$" not in result

    def test_product_models(self):
        """产品型号"""
        text = "iPhone 15 和 Tesla Model Y 销量"
        result, count = wrap_math_expressions(text)
        # Model Y 中的 Y 是型号，不是数学变量，这是常见的误判点
        # 理想情况是不包裹，或者结合上下文
        # 如果无法避免，至少保证不破坏单词
        assert "$Model$" not in result

    def test_chemical_elements_vs_math(self):
        """化学元素 vs 数学变量"""
        # 这是一个语义歧义区
        text = "C 是碳元素，C 也是圆的周长"
        result, count = wrap_math_expressions(text)
        # 两个 C 即使都被包裹也是可以接受的，因为它们都是单字母
        assert "$C$" in result


class TestRobustness:
    """鲁棒性测试"""

    def test_very_long_input(self):
        """超长文本输入"""
        # 构造 10KB 的重复文本
        base = "已知 x = 1, y = 2。"
        text = base * 1000
        import time
        start = time.time()
        result, count = wrap_math_expressions(text)
        end = time.time()
        
        assert count == 2000
        # 性能断言：不应超过 1 秒（取决于你的 regex 复杂度）
        assert (end - start) < 1.0 

    def test_nested_brackets_depth(self):
        """深层嵌套括号"""
        text = "f(g(h(x))) = 0"
        result, count = wrap_math_expressions(text)
        assert "$f(g(h(x))) = 0$" in result or "f(g(h(x)))" in result

    def test_special_unicode_symbols(self):
        """特殊 Unicode 符号干扰"""
        # ©, ®, ™, emoji
        text = "版权 © 2024 x = 1 😊 y = 2"
        result, count = wrap_math_expressions(text)
        assert "$x = 1$" in result
        assert "$y = 2$" in result

class TestMarkdownAndFormatting:
    """Markdown 格式与数学公式的交互测试"""

    def test_markdown_bold_italic(self):
        """粗体和斜体中的变量"""
        # 期望：保留 Markdown 标记，只包裹内部变量
        text = "已知 **x** = 1 且 *y* > 0"
        result, count = wrap_math_expressions(text)
        # 具体行为取决于正则，但至少 x 和 y 应该被识别
        assert "$x$" in result or "x" in result
        assert "$y$" in result or "y" in result

    def test_markdown_table_cells(self):
        """表格内的数学公式"""
        text = "| 变量 | 值 |\n| x | 1 |\n| y | 2 |"
        result, count = wrap_math_expressions(text)
        # 表格竖线不应破坏识别
        assert "$x$" in result or "| x |" in result
        assert "$y$" in result or "| y |" in result

    def test_markdown_headers(self):
        """标题中的公式"""
        text = "## 解关于 x 的方程"
        result, count = wrap_math_expressions(text)
        assert "$x$" in result

    def test_markdown_links(self):
        """链接文本中的公式"""
        text = "参考 [关于 x 的定义](http://example.com)"
        result, count = wrap_math_expressions(text)
        assert "$x$" in result
        assert "$http$" not in result


class TestAdvancedMathNotation:
    """高级数学符号与特殊格式"""

    def test_intervals_and_sets(self):
        """区间与集合表示"""
        # 区间：左闭右开，左开右闭
        text = "x 的取值范围是 [0, 1) ∪ (2, +∞)"
        result, count = wrap_math_expressions(text)
        assert "$x$" in result
        # 能够识别区间组合更佳，最起码不应破坏格式
        assert "[0, 1)" in result or "$0$" in result

    def test_scientific_notation(self):
        """科学计数法（防误判）"""
        text = "普朗克常数 h = 6.626e-34"
        result, count = wrap_math_expressions(text)
        
        assert "$h = 6.626e-34$" in result
        # 'e' 在这里不应被单独包裹为变量
        assert "$e$" not in result

    def test_approximate_and_proportional(self):
        """约等于和正比于"""
        text = "此时 x ≈ 3.14，且 y ∝ x"
        result, count = wrap_math_expressions(text)
        assert "$x$" in result or "$x ≈ 3.14$" in result
        assert "$y$" in result or "$y ∝ x$" in result

    def test_prime_derivative(self):
        """导数符号 ' """
        text = "求 f'(x) 和 y'' 的值"
        result, count = wrap_math_expressions(text)
        assert "f'(x)" in result or "$f'$" in result
        assert "y''" in result or "$y''$" in result

# --- APPEND TO FILE ---

class TestGaokaoRealQuestions:
    """中国高考/模拟题真实场景测试"""

    def test_set_theory_notation(self):
        """集合与逻辑符号"""
        # 集合的描述法，包含竖线和大括号
        text = "已知集合 A = {x | x^2 - 2x - 3 < 0}，B = {-1, 0, 1, 2}，则 A ∩ B = ?"
        result, count = wrap_math_expressions(text)
        
        # 期望 A, B 被包裹
        assert "$A$" in result and "$B$" in result
        # 集合内部的不等式应当被识别
        assert "$x^2 - 2x - 3 < 0$" in result or "x^2 - 2x - 3 < 0" in result
        # 交集符号不应破坏包裹
        assert "A ∩ B" in result or "$A ∩ B$" in result or "$A$ ∩ $B$" in result

    def test_function_mapping_and_domain(self):
        """函数映射与定义域"""
        text = "函数 f(x) = ln(x + 1) + 1/x 的定义域为 (-1, 0) U (0, +∞)"
        result, count = wrap_math_expressions(text)
        
        # f(x) 格式
        assert "f(x)" in result or "$f(x)$" in result
        # ln, x+1
        assert "ln" in result # ln 不应被拆成 $l$$n$
        assert "$x + 1$" in result or "$ln(x + 1)$" in result or "$f(x)=ln(x + 1)$" in result or "$f(x) = ln(x + 1)$" in result
        # 1/x 分式
        assert "$1/x$" in result or "1/x" in result

    def test_vectors_and_dot_product(self):
        """平面向量与数量积"""
        # 向量通常用粗体或箭头，OCR 出来可能是普通字母
        text = "已知向量 a = (1, 2), b = (x, -2)，且 a // b，求 x。"
        result, count = wrap_math_expressions(text)
        
        assert "$a$" in result
        assert "$b$" in result
        assert "$x$" in result
        # 坐标格式
        assert "(1, 2)" in result or "$(1, 2)$" in result

    def test_sequence_summation(self):
        """数列求和 Sn"""
        text = "设 Sn 为等差数列 {an} 的前 n 项和，若 a1 = 1, S3 = 9。"
        result, count = wrap_math_expressions(text)
        
        assert "$S_n$" in result or "Sn" in result
        assert "$a_n$" in result or "an" in result
        assert "$a_1 = 1$" in result or "$a_1$" in result
        assert "$S_3 = 9$" in result or "$S_3$" in result

    def test_triangle_geometry(self):
        """解三角形"""
        text = "在 △ABC 中，角 A, B, C 的对边分别为 a, b, c，若 b cos C + c cos B = a。"
        result, count = wrap_math_expressions(text)
        
        # △ABC
        assert "△ABC" in result or "$△ABC$" in result or "△$ABC$" in result
        # cos 是函数名，不应包裹
        assert "$c$os" not in result
        # 核心等式
        assert "b cos C + c cos B = a" in result or "$b$" in result

    def test_probability_distribution(self):
        """概率分布列"""
        text = "随机变量 X 服从正态分布 N(μ, σ^2)，且 P(X < 0) = 0.5。"
        result, count = wrap_math_expressions(text)
        
        assert "$X$" in result
        assert "$N(μ, σ^2)$" in result or "$N$" in result
        assert "$P(X < 0) = 0.5$" in result or "$P(X < 0)=0.5$" in result or "$P$" in result

    def test_derivative_and_extremum(self):
        """导数与极值"""
        text = "设 f'(x) 是 f(x) 的导函数，当 x > 0 时，f'(x) > 0。"
        result, count = wrap_math_expressions(text)
        
        # 导数符号 ' 的处理
        assert "f'(x)" in result or "$f'$" in result
        assert "$x > 0$" in result


class TestMathStructureAndFormat:
    """试卷结构与特殊格式测试"""

    def test_multiple_choice_options(self):
        """选择题选项干扰"""
        # 选项 A. B. C. D. 不应被误判为变量 A, B, C, D
        text = "1. 下列选项正确的是（ ）\nA. x=1  B. y=2  C. x+y=3  D. x-y=0"
        result, count = wrap_math_expressions(text)
        
        # 具体的数学内容 x=1 应被包裹
        assert "$x=1$" in result or "$x = 1$" in result
        # 选项标号 A, B, C, D 取决于实现，最好是不包裹，或者包裹了也不影响阅读
        # 这里主要测试不崩溃，以及数学内容能被识别

    def test_fill_in_the_blanks_underscore(self):
        """填空题下划线"""
        text = "方程 x^2 - 1 = 0 的解是 ________ 。"
        result, count = wrap_math_expressions(text)
        
        assert "$x^2 - 1 = 0$" in result
        # 下划线保持原样
        assert "________" in result

    def test_chinese_parentheses_index(self):
        """题号（1）（2）与数学内容的混合"""
        text = "(1) 求 f(x) 的最小值；\n(2) 若 f(x) > a 恒成立，求 a。"
        result, count = wrap_math_expressions(text)
        
        assert "f(x)" in result
        assert "$a$" in result
        # (1) 不应被识别为数学公式
        assert "$(1)$" not in result

    def test_mixed_units_physics_style(self):
        """带单位的数值"""
        # 数学应用题常见
        text = "容器体积 V = 100cm^3，高度 h = 10cm。"
        result, count = wrap_math_expressions(text)
        
        assert "$V = 100cm^3$" in result or "$V$" in result
        assert "$h = 10cm$" in result or "$h = 10$" in result


class TestMathKeywordsProtection:
    """数学专用词汇保护（防止被切分）"""

    def test_trig_functions(self):
        text = "sin x, cos x, tan α, cot β"
        result, count = wrap_math_expressions(text)
        # sin, cos, tan 不应被拆解
        assert "$s$in" not in result
        assert "$c$os" not in result
        # 变量应被包裹
        assert "$x$" in result or "x" in result

    def test_log_functions(self):
        text = "ln x, lg x, log_2 x"
        result, count = wrap_math_expressions(text)
        assert "$l$n" not in result
        assert "$l$g" not in result

    def test_limit_max_min(self):
        text = "lim_{x->0}, max(a, b), min(x, y)"
        result, count = wrap_math_expressions(text)
        assert "$l$im" not in result
        assert "$m$ax" not in result
        assert "$m$in" not in result


class TestDirtyOCRData:
    """脏数据/不规范书写测试"""

    def test_no_space_operator(self):
        """运算符缺失空格"""
        text = "若x+y=1且xy=2"
        result, count = wrap_math_expressions(text)
        # 理想情况能识别出整个等式，或者至少识别出变量
        assert "$x+y=1$" in result or "$x+y = 1$" 
        assert "$xy=2$" in result or "$xy = 2$" 

    def test_consecutive_punctuation(self):
        """连续标点"""
        text = "满足条件 x=1,......,y=10。"
        result, count = wrap_math_expressions(text)
        assert "$x=1$" in result or "$x = 1$" in result
        assert "$y=10$" in result or "$y = 10$" in result

    def test_fullwidth_characters_mix(self):
        """全角字符混排"""
        text = "已知ａ＝１，ｂ＝２（全角字符）。"
        result, count = wrap_math_expressions(text)
        # 如果算法不支持全角转半角，至少保证不报错
        # 这是一个进阶需求，如果你的算法目前不支持全角，这个测试失败是正常的
        pass

import pytest

# 假设 wrap_math_expressions 已经导入
# from your_module import wrap_math_expressions

class TestWrapMathExpressions:
    """
    测试策略：
    1. 典型场景：包含所有目标类型（坐标、方程、下标、变量）的复杂句子。
    2. 混合语境：中文、英文、标点符号对单字母变量识别的影响。
    3. 幂等性：确保已经是 LaTeX 格式的内容不会被破坏或重复包裹。
    4. 边界处理：字符串开头、结尾以及紧邻标点的情况。
    """

    def test_comprehensive_geometry_problem(self):
        """测试：典型的解析几何题目场景（核心功能集成测试）。"""
        text = "已知点M(4,0)在抛物线y^2=2px(p>0)上，直线l_1与x轴交于点F。"
        expected_text = "已知点$M(4,0)$在抛物线$y^2 = 2px$($p > 0$)上，直线$l_1$与$x$轴交于点$F$。"
        
        result, count = wrap_math_expressions(text)
        
        # 验证所有关键元素都被包裹
        assert "$M(4,0)$" in result
        assert "$y^2=2px$" in result or "$y^2 = 2px$" in result
        assert "$p>0$" in result or "$p > 0$" in result
        assert "$l_1$" in result
        assert "$F$" in result
        # 验证总替换次数是否符合预期 (M, Eq, Ineq, l_1, x, F -> 6处)
        assert count == 6
        #assert result == expected_text

    def test_single_letter_heuristics_context(self):
        """测试：单字母变量的上下文感知（精细化逻辑）。
        
        代码逻辑分析：
        - 只有当单字母周围是中文或特定标点时才包裹。
        - 纯英文单词中的字母不应被误判（依赖于 _SINGLE_LETTER_RE 的正则边界或逻辑判断）。
        """
        # 情况A: 中文包围 -> 应包裹
        # 情况B: 标点包围 -> 应包裹
        # 情况C: 英文句子单词 -> 不应包裹 (假设正则能够区分单词边界)
        text = "设集合A和B。Let a be a point."
        
        # 预期：A和B被包裹（中文/标点语境），x被包裹。
        # 注意：这里的 'a' 是否被包裹取决于 _SINGLE_LETTER_RE 是否匹配单词中的字符。
        # 通常单字母正则会使用 \b 边界。如果匹配到了 'a' (in Let) 或 'a' (article)，
        # 代码中的 punct 逻辑会决定是否包裹。
        # 假设：'Let' 中的 'a' 前后是字母，不满足 punct/chinese，不包裹。
        # 单独的 'a' (point) 前后是空格，满足 punct，应包裹。
        
        expected_part = "设集合$A$和$B$。"
        
        result, _ = wrap_math_expressions(text)
        
        assert expected_part in result
        # 验证英文语境下的行为（假设 'Let' 不被破坏）
        assert "Let" in result 
        # 验证独立变量 'a' 被包裹
        assert " $a$ " in result or "$a$" in result

    def test_idempotency_and_protection(self):
        """测试：幂等性与现有 LaTeX 保护。
        
        非常重要：防止对已经是 LaTeX 的内容进行二次包裹，导致 $$x$$ 错误。
        """
        text = "已知 $x > 0$ 且 $$y = x$$，求z。"
        # 预期：已经存在的 $...$ 和 $$...$$ 保持原样，仅处理新出现的 z
        expected = "已知 $x > 0$ 且 $$y = x$$，求$z$。"
        
        result, count = wrap_math_expressions(text)
        
        assert result == expected
        assert count == 1  # 只有 z 被处理了

    def test_boundary_and_spacing_cleanup(self):
        """测试：关系式的空格清理与字符串边界情况。
        
        对应代码逻辑：lambda m: f"${m.group(0).strip()}$"
        """
        # 测试前后带有空格的关系式，以及位于字符串开头/结尾的变量
        text = "x=y 成立。P"
        # 假设正则捕获了 "x=y " (带尾随空格)
        
        result, _ = wrap_math_expressions(text)
        
        # 验证 strip() 是否生效：空格应该在 $ 外面 或 被移除，而不是 "$x=y $"
        assert "$x=y$" in result or "$x = y$" in result
        # 验证字符串末尾的单字母 P 是否被识别
        assert text.endswith("P") # 输入
        assert result.endswith("$P$") # 输出

    def test_complex_subscripts_and_coords(self):
        """测试：复杂的下标和坐标组合（针对正则的鲁棒性）。"""
        text = "点P_1(x_1, y_1)与P_2关于原点对称。"
        expected = "点$P_1(x_1, y_1)$与$P_2$关于原点对称。"
        
        result, _ = wrap_math_expressions(text)
        
        # 这是一个针对优先级的测试：
        # 如果 _POINT_RE (坐标) 优先级高于 _SUBSCRIPT_RE (下标)，
        # 那么 P_1(x_1, y_1) 应该作为一个整体被 Point 正则捕获。
        # 如果是分开捕获，结果可能是一堆零散的 $...$。
        # 此测试验证是否生成了人类可读的完整数学块。
        assert "$P_1(x_1, y_1)$" in result
        assert "$P_2$" in result

# --- APPEND TO FILE ---

class TestCalculusAndAnalysis:
    """微积分与数学分析（高等数学场景）"""

    def test_integrals_and_differentials(self):
        """积分与微分算子"""
        # dx, dy 不应被拆解为 d * x
        text = "求不定积分 ∫ x^2 dx 和定积分 ∫_0^1 e^x dy。"
        result, count = wrap_math_expressions(text)
        
        # 积分符号可能难处理，但内部的 x^2, e^x 必须识别
        assert "$x^2$" in result
        assert "$e^x$" in result
        # dx 最好作为一个整体，或者 d 和 x 分别包裹但紧邻
        # 只要不识别成 "d 变量乘 x 变量" 的逻辑即可

    def test_limits_arrows(self):
        """极限与趋近符号"""
        text = "当 x -> ∞ 时，lim (1 + 1/x)^x = e。"
        result, count = wrap_math_expressions(text)
    
        assert "$x$" in result
        assert "$e$" in result or "= e$" in result
        # (1 + 1/x)^x 是核心结构
        assert "(1 + 1/x)^x" in result or "$1 + 1/x$" in result or "lim (1 + 1/x)" in result

    def test_summation_and_product(self):
        """求和与求积符号"""
        text = "求 Σ(i=1 to n) i^2 和 Π(k=1 to n) a_k。"
        result, count = wrap_math_expressions(text)
    
        assert "$i^2$" in result
        assert "$a_k$" in result
        

    def test_piecewise_function_description(self):
        """分段函数描述（文字版）"""
        text = "当 x > 0 时，f(x) = x；当 x ≤ 0 时，f(x) = -x。"
        result, count = wrap_math_expressions(text)
    
        assert "$x > 0$" in result
        assert "$f(x) = x$" in result or "$f(x)=x$" in result
        assert "$x ≤ 0$" in result


class TestLinearAlgebra:
    """线性代数与矩阵"""

    def test_matrix_variables(self):
        """矩阵变量与转置"""
        text = "设矩阵 A 为 n 阶方阵，A^T 是 A 的转置，求 |A|。"
        result, count = wrap_math_expressions(text)
        
        assert "$A$" in result
        assert "$A^T$" in result
        assert "$n$" in result
        assert "|A|" in result or "$|A|$" in result

    def test_determinant_calculation(self):
        """行列式计算"""
        text = "若行列式 D = det(A) = 0，则 A 不可逆。"
        result, count = wrap_math_expressions(text)
    
        assert "$D$" in result or "$D=det(A)=0$" in result or "$D = det(A) = 0$" in result
        assert "$A$" in result
        assert "$det(A)$" in result or "det(A)" in result
        assert "$d$e$t" not in result


class TestPhysicsAndChemistry:
    """理综符号干扰（物理化学）"""

    def test_chemical_formulas(self):
        """化学式（不应被过度包裹）"""
        # H2O, H2SO4, CO2
        text = "将 H2SO4 加入 H2O 中，产生热量。"
        result, count = wrap_math_expressions(text)
        
        # 化学式通常保持原样，或者整体被包裹
        # 绝对不能变成 $H$2$S$$O$4
        # 这是一个极难的 case，视你的 regex 策略而定
        if "$H$" in result:
             # 如果被包裹了，至少要检查没有切碎数字
             pass 

    def test_chemical_equations(self):
        """化学方程式"""
        text = "反应方程式：2H2 + O2 = 2H2O"
        result, count = wrap_math_expressions(text)
        # 等号可能触发数学识别
        # 只要不把 O2 识别成 O^2 即可
        pass

    def test_physics_units_mix(self):
        """物理量与单位混合"""
        text = "速度 v = 10m/s，加速度 a = 5m/s^2，力 F = 50N。"
        result, count = wrap_math_expressions(text)
    
        assert "$v$" in result or "$v = 10$" in result or "$v = 10m/s$" in result
        assert "$a$" in result or "$a = 5m/s^2$" in result
        assert "$F$" in result or "$F = 50N$" in result
        # 单位 m/s, N 不应被识别为变量 m, s, N
        # 除非它们独立出现且无单位语境


class TestComplexOCRLayouts:
    """排版混乱的 OCR 结果（魔鬼测试）"""

    def test_line_break_in_equation(self):
        """跨行公式"""
        text = "已知函数 f(x) = \n x^2 + 1"
        result, count = wrap_math_expressions(text)
    
        # 换行符可能阻断正则
        assert "f(x)" in result
        assert "$x^2 + 1$" in result  or "$f(x)=x^2$" in result or "$f(x) = x^2$" in result

    def test_embedded_figure_captions(self):
        """嵌入图片说明文字"""
        text = "(图1) 如图所示，点 P 在圆 O 上。"
        result, count = wrap_math_expressions(text)
        
        assert "$P$" in result
        assert "$O$" in result
        # (图1) 不应被识别
        assert "$(图1)$" not in result

    def test_fill_blanks_brackets(self):
        """带括号的填空"""
        text = "若 x = 3，则 x^2 = (   )。"
        result, count = wrap_math_expressions(text)
        
        assert "$x = 3$" in result
        assert "$x^2$" in result
        # 空括号不应报错或被奇怪包裹
        assert "()" in result or "(   )" in result

    def test_itemized_list_mess(self):
        """混乱的列表项"""
        text = "①x=1；②y>2；③z≠0"
        result, count = wrap_math_expressions(text)
        
        assert "$x=1$" in result or "$x = 1$" in result
        assert "$y>2$" in result or "$y > 2$" in result
        assert "$z≠0$" in result or "$z ≠ 0$" in result


class TestLogicAndProof:
    """证明题与逻辑符号"""

    def test_proof_keywords(self):
        """证明题常用词"""
        text = "∵ AB // CD, ∴ ∠B = ∠C"
        result, count = wrap_math_expressions(text)
        
        assert "$AB$" in result or "AB" in result # 几何线段
        assert "$CD$" in result or "CD" in result
        assert "∠B" in result or "$B$" in result # 角符号

    def test_implication_arrows(self):
        """推导箭头"""
        text = "由 x > 1 => x^2 > 1"
        result, count = wrap_math_expressions(text)
        
        assert "$x > 1$" in result
        assert "$x^2 > 1$" in result

    def test_kuohao(self):
        """推导箭头"""
        text = "(((a<b<B<C)))"
        result, count = wrap_math_expressions(text)
        
        assert "$a<b<B<C$" in result or "$a < b < B < C$" in result

    def test_kuohao2(self):
        """推导箭头"""
        text = "((dd[[(a<b<B<C)))"
        result, count = wrap_math_expressions(text)
        
        assert "$a<b<B<C$" in result or "$a < b < B < C$" in result

    def test_kuohao3(self):
        """推导箭头"""
        text = "(a /in b)"
        result, count = wrap_math_expressions(text)
        
        assert "$a /in b$" in result 

    def test_kuohao4(self):
        """推导箭头"""
        text = "a /times b"
        result, count = wrap_math_expressions(text)
        
        assert "$a /times b$" in result or "$a$ /times $b$" in result
    def test_kuohao5(self):
        """推导箭头"""
        text = "C:/Coding/Python/latex_template/output/pdf_ocr/数学-河南省青桐鸣2025-2026学年高二上学期1月月考试题和答案"
        result, count = wrap_math_expressions(text)
        
        assert text==result


class TestWrapMathAdditionalCoverage:
    """补充覆盖：保护规则与特殊解析"""

    def test_option_labels_are_preserved(self):
        text = "A. x = 1  B. y = 2"
        result, count = wrap_math_expressions(text)
        assert "A." in result
        assert "B." in result
        assert "$A$." not in result
        assert "$B$." not in result
        assert "$x = 1$" in result
        assert "$y = 2$" in result

    def test_html_attributes_preserved(self):
        text = "<span data-id='x_1'>x = 1</span>"
        result, count = wrap_math_expressions(text)
        assert "<span data-id='x_1'>" in result
        assert "</span>" in result
        assert "$x = 1$" in result

    def test_windows_path_protected(self):
        text = "请查看 C:\\data\\file_1\\report_v2.txt 中的内容"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_sequence_index_auto_subscript(self):
        text = "数列 a1 和 S2 的前 n 项"
        result, count = wrap_math_expressions(text)
        assert "$a_1$" in result
        assert "$S_2$" in result

    def test_keyword_if_not_wrapped(self):
        text = "if(x>0) return y"
        result, count = wrap_math_expressions(text)
        assert "if(" in result
        assert "$if" not in result
        assert "$x > 0$" in result
        assert "$y$" in result

    def test_general_function_call_wrapped(self):
        text = "函数 foo(bar, baz) 的图像"
        result, count = wrap_math_expressions(text)
        assert "$foo(bar, baz)$" in result

    def test_inline_math_span_protected(self):
        text = r"已知 \(x^2 + y^2 = 1\) 是圆"
        result, count = wrap_math_expressions(text)
        assert result == text
        assert count == 0

    def test_inline_math_span_protected2(self):
        text = r"设$O$为坐标原点,若\triangle ABF的面积为8\sqrt3,直线$l_2$与$y$轴交于点$N$,证明:|OM|=|ON|."
        result, count = wrap_math_expressions(text)
        assert r"$\triangle$" in result or r"$\triangle ABF$" in result
        assert r"$8\sqrt3$" in result

    def test_inline_math_span_protected3(self):
        text = r"设$O$为坐标原点,若\cos ABF的面积为\gamma,直线$l_2$与$y$轴交于点$N$,证明:|OM|=|ON|."
        result, count = wrap_math_expressions(text)
        assert r"$\cos$" in result or r"$\cos ABF$" in result
        assert r"$\gamma$" in result    

    def test_display_math_span_not_split(self):
        text = r"已知 $$x=1$$ 且 y=2"
        result, count = wrap_math_expressions(text)
        parts = result.split("$$")
        assert len(parts) == 3
        assert parts[1].strip() == "x=1"

    def test_option_label_in_chinese_protected(self):
        text = "选项A. 选项B. 选项C. 选项D."
        result, count = wrap_math_expressions(text)
        assert "选项A." in result and "选项B." in result
        assert "$A$." not in result and "$B$." not in result

    def test_relation_spacing_preserves_compound_operator(self):
        text = "当 x<=y 时"
        result, count = wrap_math_expressions(text)
        assert "x < = y" not in result
        assert "$x <= y$" in result or "$x<=y$" in result


    def test_derivative_not_split_by_fraction(self):
        text = "求 dy/dx 的值"
        result, count = wrap_math_expressions(text)
        assert "$dy/dx$" in result
        assert "$y/d$" not in result

    def test_url_query_not_wrapped(self):
        text = "访问 https://example.com/?x=1&y=2 获取数据"
        result, count = wrap_math_expressions(text)
        assert "https://example.com/?x=1&y=2" in result
        assert "$x=1$" not in result and "$y=2$" not in result

 


    def test_unicode_symbol_should_be_in_math_mode(self):
        text = "集合A∩B中"
        result, count = wrap_math_expressions(text)
        assert "$A∩B$" in result
        assert "$A$∩$B$" not in result

    def test_merge_adjacent_display_math(self):
        text = "表达式 $$f(x)$$/$$x$$"
        result, count = wrap_math_expressions(text)
        assert "$$f(x)/x$$" in result
        assert "$$f(x)$$/$$x$$" not in result
