# -*- coding: utf-8 -*-
from math_digitizer.core.validator import wrap_math_expressions

tests = [
    ('集合', '已知集合 A={x| -1<x<2 }'),
    ('复数', '若复数 z 满足 z(1+i)=2i'),
    ('引号不等式', '"x>1" 是什么条件'),
    ('函数定义域', '函数 f(x)=ln(2-x) 的定义域是 [1,2)'),
    ('坐标点', '曲线在点 P(1, -2) 处'),
    ('希腊字母', '已知 a>0，函数 f(x)=sin(ax+b)'),
    ('无空格', '设f(x)=lnx-a/x'),
    ('立体几何', '在四棱锥 P-ABCD 中，底面 ABCD 是直角梯形'),
    ('概率分布', '随机变量 X 服从正态分布 N(1, 2)'),
    ('数列下标', '设等差数列 {an} 的公差 d≠0，若 a1, a2, a5 成等比'),
]

for name, t in tests:
    result, count = wrap_math_expressions(t)
    print(f'{name}:')
    print(f'  输入: {t}')
    print(f'  输出: {result}')
    print(f'  包裹: {count}')
    print()
