import json
import os
import re
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class ExamGenerator:
    def __init__(self, template_file='exam_template.txt'):
        self.template_file = template_file
        self._image_defaults = {
            "width": r"0.6\textwidth",
            "height": r"0.25\textheight",
        }

        template_path = Path(template_file)
        if not template_path.is_absolute():
            cwd_candidate = Path.cwd() / template_path
            root_candidate = Path(__file__).resolve().parent.parent / template_path
            if cwd_candidate.exists():
                template_path = cwd_candidate
            elif root_candidate.exists():
                template_path = root_candidate
            else:
                template_path = root_candidate

        self._template_path = template_path
        self._template_name = template_path.name

        # 配置 Jinja2 以使用 LaTeX 友好的分隔符
        self.env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
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
            print(f"[error] File not found: {filename}")
            return None
        except Exception as e:
            print(f"[error] Failed to read file: {e}")
            return None

    def process_data(self, json_str):
        """
        数据清洗管道
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[error] JSON parse error: {e}")
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

                # 4. (æ–°å¢ž) image å ä½å¤„ç†ï¼Œç”¨äºŽé¢„ç•™å›¾ç‰‡ä½ç½®
                img = q.get("image")
                if img is None:
                    q["image"] = None
                elif isinstance(img, dict):
                    for k, v in self._image_defaults.items():
                        if not img.get(k):
                            img[k] = v
                    q["image"] = img
                elif isinstance(img, str):
                    q["image"] = {
                        "width": self._image_defaults["width"],
                        "height": self._image_defaults["height"],
                    }
                elif isinstance(img, bool) and img:
                    q["image"] = dict(self._image_defaults)
                else:
                    q["image"] = None

        return data

    def render(self, data, output_tex='math_exam.tex'):
        """渲染 LaTeX 模板"""
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_tex)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"[info] Created output directory: {output_dir}")

            template = self.env.get_template(self._template_name)
            rendered_tex = template.render(data)
            
            with open(output_tex, 'w', encoding='utf-8') as f:
                f.write(rendered_tex)
            print(f"[ok] LaTeX generated: {output_tex}")
            return output_tex
        except Exception as e:
            print(f"[error] Template render failed: {e}")
            return None

    def compile_pdf(self, tex_file, *, passes: int = 2):
        """调用 xelatex 编译 PDF（默认两次以修复页码/引用）"""
        if not tex_file:
            return False

        print(f"[info] Compiling PDF (pass 1/{passes})...")
        
        output_dir = os.path.dirname(tex_file)
        tex_path = Path(tex_file)
        log_capture_path = (Path(output_dir) if output_dir else tex_path.parent) / f"{tex_path.stem}.xelatex.txt"
        # 构建命令: xelatex -interaction=nonstopmode -output-directory=DIR FILE
        cmd = ['xelatex', '-interaction=nonstopmode']
        
        if output_dir:
            cmd.append(f'-output-directory={output_dir}')
            
        cmd.append(tex_file)

        try:
            with open(log_capture_path, "a", encoding="utf-8", errors="replace") as logf:
                for i in range(passes):
                    logf.write(f"\n===== xelatex pass {i+1}/{passes} =====\n")
                    subprocess.run(cmd, check=True, stdout=logf, stderr=logf)
                    if i + 1 < passes:
                        print(f"[info] Compiling PDF (pass {i+2}/{passes})...")

            print(f"[ok] PDF compiled: {tex_file.replace('.tex', '.pdf')}")
            print(f"[info] xelatex output captured: {log_capture_path}")
            return True
            
        except FileNotFoundError:
            print("[error] xelatex not found. Please install TeX Live / MiKTeX and ensure xelatex is in PATH.")
            return False
        except subprocess.CalledProcessError:
            tex_log = tex_file.replace(".tex", ".log")
            print("[error] LaTeX compile failed.")
            print(f"[info] Check TeX log: {tex_log}")
            print(f"[info] Check xelatex output: {log_capture_path}")
            return False

'''
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
'''
