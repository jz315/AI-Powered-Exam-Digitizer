import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from math_digitizer.utils.paths import get_resource_path

class ExamGenerator:
    def __init__(self, template_file='exam_template.txt'):
        self.template_file = template_file
        self._image_defaults = {
            "width": r"0.6\textwidth",
            "height": r"0.25\textheight",
        }
        self._md_image_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

        template_path = Path(template_file)
        if not template_path.is_absolute():
            cwd_candidate = Path.cwd() / template_path
            resource_candidate = get_resource_path("resources") / template_path
            if cwd_candidate.exists():
                template_path = cwd_candidate
            elif resource_candidate.exists():
                template_path = resource_candidate
            else:
                template_path = resource_candidate

        self._template_path = template_path
        self._template_name = template_path.name

        # 闁板秶鐤� Jinja2 娴犮儰濞囬悽?LaTeX 閸欏銈介惃鍕瀻闂呮梻顑�
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
        """娴�?JSON 閺傚洣娆㈢拠璇插絿閺佺増宓�"""
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
        閺佺増宓佸〒鍛缁狅繝浜�
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[error] JSON parse error: {e}")
            return None

        # 闁秴宸婚幍鈧張澶娿亣妫�?
        for section in data.get('sections', []):
            # 闁秴宸婚幍鈧張澶婄毈妫�?
            for q in section.get('questions', []):
                # 1. 婢跺嫮鎮婃繅顐も敄妫版ê宕版担宥囶儊
                if "__BLANK__" in q.get('content', ''):
                    # 閺囨寧宕叉稉?\fillin[]閿涘奔鑵戦幏顒€褰块崘鍛礋缁岄缚銆冪粈楦垮殰閸斻劏顓哥粻妤呮毐鎼�?
                    q['content'] = q['content'].replace("__BLANK__", r"\fillin[]")
                
                # 2. 婢跺嫮鎮婇柅澶嬪妫版﹢鈧銆嶉敍姘箵閹�?A. B. 缁涘澧犵紓鈧�
                if 'options' in q:
                    q['options'] = [re.sub(r'^[A-D]\.\s*', '', opt) for opt in q['options']]
                
                # 3. (閺傛澘顤�) 濡偓閺�?figure 鐎涙顔岄惃鍕暚閺佸瓨鈧�?
                # 婵″倹鐏� figure 娑�?null 閹�?type 娑撳秵妲� tikz閿涘瞼鈥樻穱婵嚹侀弶鑳厴鐎瑰鍙忔径鍕倞
                if 'figure' not in q or q['figure'] is None:
                    q['figure'] = None

                # 4. (蹇欓垾鎾€鎳娿儌鈶�? image 姘撹仹鑱界洸闄嗚仹姘撻檱閳ョ伝顬犳劏鈧妴顕峰瘋鎹椦€鈧緵顭嬨仮鍙风煫鈹炩懇鈧伝褉鈧懇鍔夋皳閳ラ儩涔呇€鈧壋鈧埗銇㈤摪宓滎灎閾�?
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


    def replace_inline_images(self, data, asset_dir: str, *, asset_rel: str = "assets", width: str = r"0.3\linewidth") -> tuple[list[str], list[str]]:
        """
        Replace inline markdown images with LaTeX includegraphics.
        
        Returns:
            tuple: (missing_images, warnings)
                - missing_images: List of image paths that couldn't be found
                - warnings: List of validation warning messages
        """
        warnings: list[str] = []
        
        if not data:
            warnings.append("No data provided for image processing")
            return [], warnings

        image_base_dir = data.get("meta", {}).get("image_base_dir", "")
        if not image_base_dir:
            warnings.append("JSON中缺少 meta.image_base_dir 字段，跳过图片处理。请确保AI输出包含此字段。")
            return [], warnings
        
        base_path = Path(image_base_dir)
        if not base_path.exists():
            warnings.append(f"图片目录不存在: {image_base_dir}")
            return [], warnings

        missing: list[str] = []
        counter = 0
        asset_root = Path(asset_dir)
        asset_root.mkdir(parents=True, exist_ok=True)

        def resolve_source(path_str: str) -> Path | None:
            raw = path_str.strip().strip("\"").strip("'")
            if not raw:
                return None
            try:
                from urllib.parse import unquote as _unquote
                raw = _unquote(raw)
            except Exception:
                pass
            
            filename = Path(raw).name
            candidate = base_path / filename
            if candidate.exists():
                return candidate
            return None

        def copy_to_assets(src_path: str) -> str | None:
            nonlocal counter
            src = resolve_source(src_path)
            if src is None:
                return None
            counter += 1
            ext = src.suffix if src.suffix else ".png"
            dest_name = f"img-{counter:04d}{ext}"
            
            dest = asset_root / dest_name
            try:
                shutil.copy2(src, dest)
            except Exception:
                return None
            rel = f"{asset_rel}/{dest_name}"
            return rel.replace("\\", "/")

        def replace_in_text(text: str) -> str:
            if not isinstance(text, str):
                return text

            def repl(match: re.Match) -> str:
                path_str = match.group(1)
                rel = copy_to_assets(path_str)
                if not rel:
                    missing.append(path_str)
                    return r"\fbox{Missing image}"
                return r"\includegraphics[width=" + width + r"]{" + rel + r"}"

            return self._md_image_pattern.sub(repl, text)

        def walk_question(q: dict) -> None:
            if "content" in q and isinstance(q.get("content"), str):
                q["content"] = replace_in_text(q["content"])
            if "options" in q and isinstance(q.get("options"), list):
                q["options"] = [replace_in_text(opt) if isinstance(opt, str) else opt for opt in q["options"]]
            if "sub_questions" in q and isinstance(q.get("sub_questions"), list):
                for sub in q["sub_questions"]:
                    if isinstance(sub, dict):
                        walk_question(sub)

        for section in data.get("sections", []):
            if not isinstance(section, dict):
                continue
            for q in section.get("questions", []):
                if isinstance(q, dict):
                    walk_question(q)

        return missing, warnings

    def render(self, data, output_tex='math_exam.tex'):
        """濞撳弶鐓� LaTeX 濡剝婢�"""
        try:
            # 绾喕绻氭潏鎾冲毉閻╊喖缍嶇€涙ê婀�
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

    def compile_pdf(self, tex_file, *, passes: int = 2, cancel_check=None):
        """鐠嬪啰鏁� xelatex 缂傛牞鐦� PDF閿涘牓绮拋銈勮⒈濞嗏€蹭簰娣囶喖顦叉い鐢电垳/瀵洜鏁ら敍?"""
        if not tex_file:
            return False

        print(f"[info] Compiling PDF (pass 1/{passes})...")
        
        output_dir = os.path.dirname(tex_file)
        tex_path = Path(tex_file)
        log_capture_path = (Path(output_dir) if output_dir else tex_path.parent) / f"{tex_path.stem}.xelatex.txt"
        # 閺嬪嫬缂撻崨鎴掓姢: xelatex -interaction=nonstopmode -output-directory=DIR FILE
        cmd = ['xelatex', '-interaction=nonstopmode']
        
        if output_dir:
            cmd.append(f'-output-directory={output_dir}')
            
        cmd.append(tex_file)

        try:
            with open(log_capture_path, "a", encoding="utf-8", errors="replace") as logf:
                for i in range(passes):
                    if cancel_check and cancel_check():
                        logf.write("\n[info] Compile cancelled by user (before pass start)\n")
                        return False

                    logf.write(f"\n===== xelatex pass {i+1}/{passes} =====\n")
                    proc = subprocess.Popen(cmd, stdout=logf, stderr=logf)
                    while True:
                        if cancel_check and cancel_check():
                            logf.write("\n[info] Compile cancelled by user\n")
                            try:
                                proc.terminate()
                                proc.wait(timeout=5)
                            except Exception:
                                try:
                                    proc.kill()
                                except Exception:
                                    pass
                            return False
                        if proc.poll() is not None:
                            break
                        time.sleep(0.2)

                    if proc.returncode != 0:
                        raise subprocess.CalledProcessError(proc.returncode, cmd)

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
    
    # 鐠囪褰囬弫鐗堝祦
    input_file = 'exam_data.json'
    print(f"棣冾樆 濮濓絽婀拠璇插絿閺佺増宓侀弬鍥︽: {input_file} ...")
    
    json_content = generator.load_data_from_file(input_file)
    
    if json_content:
        exam_data = generator.process_data(json_content)
        if exam_data:
            # 鏉堟挸鍤崚?output 閺傚洣娆㈡径?
            output_path = os.path.join('output', 'math_exam.tex')
            tex_filename = generator.render(exam_data, output_path)
            
            # 缂傛牞鐦� PDF
            generator.compile_pdf(tex_filename)
'''

