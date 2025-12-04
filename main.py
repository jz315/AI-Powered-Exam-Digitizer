import json
import os
import re
import subprocess
from jinja2 import Template, Environment, FileSystemLoader

class ExamGenerator:
    def __init__(self, template_file='exam_template.tex'):
        self.template_file = template_file
        # 配置 Jinja2 以使用 LaTeX 友好的分隔符
        self.env = Environment(
            loader=FileSystemLoader('.'),
            variable_start_string='((', 
            variable_end_string='))',
            block_start_string='((*', 
            block_end_string='*))',
            comment_start_string='((#', 
            comment_end_string='#))'
        )

    def load_data_from_file(self, filename):
        """从 JSON 文件读取数据"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except FileNotFoundError:
            print(f"❌ 错误: 找不到文件 {filename}")
            return None
        except Exception as e:
            print(f"❌ 读取文件出错: {e}")
            return None

    def process_data(self, json_str):
        """
        数据清洗管道
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析错误: {e}")
            return None

        # 遍历所有大题
        for section in data.get('sections', []):
            # 遍历所有小题
            for q in section.get('questions', []):
                # 1. 处理填空题占位符
                if "__BLANK__" in q.get('content', ''):
                    # 替换为 \fillin[]，中括号内为空表示自动计算长度
                    q['content'] = q['content'].replace("__BLANK__", r"\fillin[]")
                
                # 2. 处理选择题选项：去掉 A. B. 等前缀
                if 'options' in q:
                    q['options'] = [re.sub(r'^[A-D]\.\s*', '', opt) for opt in q['options']]
                
                # 3. (新增) 检查 figure 字段的完整性
                # 如果 figure 为 null 或 type 不是 tikz，确保模板能安全处理
                if 'figure' not in q or q['figure'] is None:
                    q['figure'] = None

        return data

    def render(self, data, output_tex='math_exam.tex'):
        """渲染 LaTeX 模板"""
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_tex)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"📂 已创建输出目录: {output_dir}")

            template = self.env.get_template(self.template_file)
            rendered_tex = template.render(data)
            
            with open(output_tex, 'w', encoding='utf-8') as f:
                f.write(rendered_tex)
            print(f"✅ LaTeX 源码已生成: {output_tex}")
            return output_tex
        except Exception as e:
            print(f"❌ 渲染模板失败: {e}")
            return None

    def compile_pdf(self, tex_file):
        """调用 xelatex 编译 PDF"""
        if not tex_file:
            return

        print("⏳ 正在编译 PDF (需要安装 TeX 环境)...")
        
        output_dir = os.path.dirname(tex_file)
        # 构建命令: xelatex -interaction=nonstopmode -output-directory=DIR FILE
        cmd = ['xelatex', '-interaction=nonstopmode']
        
        if output_dir:
            cmd.append(f'-output-directory={output_dir}')
            
        cmd.append(tex_file)

        try:
            # 运行一次编译
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
            print(f"🎉 PDF 编译成功！请查看 {tex_file.replace('.tex', '.pdf')}")
            
        except FileNotFoundError:
            print("❌ 错误：未找到 xelatex 命令。请安装 TeXLive 或 MiKTeX。")
        except subprocess.CalledProcessError:
            print("❌ 编译失败，请检查生成的 .tex 文件中的 LaTeX 语法错误。")

if __name__ == "__main__":
    generator = ExamGenerator()
    
    # 读取数据
    input_file = 'exam_data.json'
    print(f"🤖 正在读取数据文件: {input_file} ...")
    
    json_content = generator.load_data_from_file(input_file)
    
    if json_content:
        exam_data = generator.process_data(json_content)
        if exam_data:
            # 输出到 output 文件夹
            output_path = os.path.join('output', 'math_exam.tex')
            tex_filename = generator.render(exam_data, output_path)
            
            # 编译 PDF
            generator.compile_pdf(tex_filename)