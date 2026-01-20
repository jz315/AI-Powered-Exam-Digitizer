import os
import sys
import subprocess
import platform
import shutil
import time

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    YELLOW = '\033[33m'
    BLUE = '\033[36m'

os.system("") 

def print_banner():
    print(Colors.OKBLUE)
    ''' 
    print(r"""
  __  __       _   _       ____  _       _ _   _              
 |  \/  | __ _| |_| |_    |  _ \(_) __  (_) |_(_)_______ _ __ 
 | |\/| |/ _` | __| '_ \  | | | | |/ _ `| | __| |_  / _ \ '__|
 | |  | | (_| | |_| | | | | |_| | | (_| | | |_| |/ /  __/ |   
 |_|  |_|\__,_|\__|_| |_| |____/|_|\__, |_|\__|_/___\___|_|   
                                   |___/                      
""")
    '''
   

    print(r"""
_______________________
|  __________________  |   __  __       _   _
| |   ___________    | |  |  \/  | __ _| |_| |__
| |   \ _________\   | |  | |\/| |/ _` | __| '_ \
| |    \ \           | |  | |  | | (_| | |_| | | |
| |     \ \_         | |  |_|  |_|\__,_|\__|_| |_|
| |     / /          | |   ____  _       _ _   _              
| |    / /________   | |  |  _ \(_) __  (_) |_(_)_______ _ __ 
| |   /__________/   | |  | | | | |/ _ `| | __| |_  / _ \ '__|
| |__________________| |  | |_| | | (_| | | |_| |/ /  __/ |   
|______________________|  |____/|_|\__, |_|\__|_/___\___|_|   
                                   |___/            
    """)
    print(Colors.ENDC,r"""
                       Hello World!
    """,f"{Colors.BOLD}欢迎使用数学试卷排版助手 (Math Digitizer) 安装程序{Colors.ENDC}")
    

    print()
    print("-" * 60)
    print()

def log(msg, type="info"):
    if type == "info":
        print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {msg}")
    elif type == "success":
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} {msg}")
    elif type == "warning":
        print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {msg}")
    elif type == "error":
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")
    elif type == "header":
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== {msg} ==={Colors.ENDC}")
    elif type == "step":
        print(f"\n{Colors.BOLD}>> {msg}{Colors.ENDC}")

def check_command(command):
    return shutil.which(command) is not None

def phase_0_preflight():
    log("阶段 0: 环境检查 (Environment Check)", "step")
    if os.path.exists(".venv"):
        print(f"\n{Colors.WARNING}[!] 检测到已存在虚拟环境 (.venv)。{Colors.ENDC}")
        choice = input(f"{Colors.BOLD}是否需要重新安装? (y/N): {Colors.ENDC}").lower()
        if choice != 'y':
            log("已跳过安装。退出程序。", "info")
            input("\n按回车键退出...")
            sys.exit(0)
        else:
            log("正在清理旧环境...", "warning")
            shutil.rmtree(".venv")
            log("清理完成。", "success")
    else:
        log("环境干净，准备安装。", "success")

def phase_1_tools():
    log("阶段 1: 检查基础工具 (Tools Check)", "step")
    
    print(" - 检查 uv 包管理器...", end=" ")
    if check_command("uv"):
        print(f"{Colors.OKGREEN}OK{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}未找到{Colors.ENDC}")
        log("未检测到 uv，正在尝试自动安装...", "warning")
        try:
            if platform.system() == "Windows":
                subprocess.check_call('powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"', shell=True)
            else:
                subprocess.check_call('curl -LsSf https://astral.sh/uv/install.sh | sh', shell=True)
            log("uv 安装成功。", "success")
        except:
            log("uv 安装失败，请手动安装。", "error")
            sys.exit(1)

    print(" - 检查 Python 环境...", end=" ")
    v = sys.version_info
    if v.major == 3 and v.minor >= 11:
        print(f"{Colors.OKGREEN}OK (v{v.major}.{v.minor}){Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}版本过低{Colors.ENDC}")
        log(f"需要 Python 3.11+，当前版本: {v.major}.{v.minor}", "error")
        sys.exit(1)

def phase_2_gpu_config():
    log("阶段 2: 硬件配置检查 (Hardware Config)", "step")
    
    system = platform.system()
    if system != "Windows":
        log(f"系统为 {system}，跳过显卡检查 (自动处理)。", "info")
        return

    has_nvidia = False
    print(" - 检查 NVIDIA 显卡...", end=" ")
    try:
        subprocess.check_output("nvidia-smi", shell=True, stderr=subprocess.STDOUT)
        has_nvidia = True
        print(f"{Colors.OKGREEN}检测到 NVIDIA 显卡{Colors.ENDC}")
    except:
        print(f"{Colors.WARNING}未检测到 (使用 CPU){Colors.ENDC}")

    config_path = "pyproject.toml"
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    needs_cpu_mode = not has_nvidia
    
    if has_nvidia:
        print(f"\n{Colors.YELLOW}注意：安装 GPU 版 PyTorch 需要下载约 4GB 依赖。{Colors.ENDC}")
        choice = input(f"{Colors.BOLD}是否安装 GPU 加速支持? (推荐选 Y) [Y/n]: {Colors.ENDC}").lower()
        if choice == 'n':
            needs_cpu_mode = True

    # Robust Block Toggling Logic
    # We define the GPU block we want to toggle
    gpu_block_start = "[tool.uv.sources]"
    
    # Check current state
    is_cpu_mode = "# [tool.uv.sources]" in content or "#[tool.uv.sources]" in content

    if needs_cpu_mode:
        if not is_cpu_mode:
            log("正在配置 CPU 模式 (注释掉 tool.uv.sources)...", "info")
            # Comment out the block keys to disable custom source
            new_content = content.replace("[tool.uv.sources]", "# [tool.uv.sources]")
            new_content = new_content.replace("torch = [", "# torch = [")
            new_content = new_content.replace("torchvision = [", "# torchvision = [")
            # Also comment lines starting with { index
            lines = new_content.splitlines()
            final_lines = []
            for line in lines:
                if '{ index = "pytorch-cu124"' in line and not line.strip().startswith("#"):
                    final_lines.append("# " + line)
                elif line.strip() == "]" and (final_lines and "# torch" in final_lines[-2]): # Heuristic for closing bracket
                     final_lines.append("# ]")
                else:
                     final_lines.append(line)
            
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("\n".join(final_lines))
            log("配置文件已更新为 CPU 模式。", "success")
        else:
            log("当前已是 CPU 模式。", "info")

    else: # GPU Mode needed
        if is_cpu_mode:
            log("正在配置 GPU 模式 (启用 tool.uv.sources)...", "info")
            # Simple uncomment
            new_content = content.replace("# [tool.uv.sources]", "[tool.uv.sources]")
            new_content = new_content.replace("# torch = [", "torch = [")
            new_content = new_content.replace("# torchvision = [", "torchvision = [")
            
            lines = new_content.splitlines()
            final_lines = []
            for line in lines:
                 # Uncomment lines that look like source entries
                 if line.strip().startswith("#") and '{ index = "pytorch-cu124"' in line:
                     final_lines.append(line.replace("# ", "", 1).replace("#", "", 1))
                 elif line.strip().startswith("#") and line.strip().endswith("]") and "]" in line:
                     # Attempt to uncomment closing brackets if they seem related
                     # This is tricky without a parser.
                     # Better approach: Just use the known template if enabling GPU.
                     final_lines.append(line.replace("# ]", "]"))
                 else:
                     final_lines.append(line)

            with open(config_path, "w", encoding="utf-8") as f:
                 f.write("\n".join(final_lines))
            log("配置文件已更新为 GPU 模式。", "success")
        else:
             log("当前已是 GPU 模式。", "info")


def phase_3_install():
    log("阶段 3: 安装项目依赖 (Installing Dependencies)", "step")
    log("正在运行 'uv sync' (首次运行可能需要较长时间，请耐心等待)...", "info")
    
    try:
        subprocess.check_call("uv sync", shell=True)
        log("依赖安装成功！", "success")
    except subprocess.CalledProcessError:
        log("安装失败。请检查网络连接。", "error")
        sys.exit(1)

def phase_4_check_latex():
    log("阶段 4: 检查 LaTeX 环境 (Check LaTeX)", "step")
    print(" - 检查 XeLaTeX...", end=" ")
    if check_command("xelatex"):
        print(f"{Colors.OKGREEN}OK{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}未找到{Colors.ENDC}")
        print(f"\n{Colors.WARNING}[!] 警告：未检测到 XeLaTeX 命令。{Colors.ENDC}")
        print("    您将无法编译生成的 PDF 试卷。")
        print("    请安装 TeX Live (推荐) 或 MiKTeX。")

def phase_5_verify():
    log("阶段 5: 最终自检 (Final Verification)", "step")
    
    print("\nVerifying PyTorch environment...")
    cmd = "uv run python -c \"import torch; print(f'PyTorch 版本: {torch.__version__}, CUDA 可用性: {torch.cuda.is_available()}')\""
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8')
        print(f"{Colors.OKGREEN}{output.strip()}{Colors.ENDC}")
    except:
        log("验证脚本运行失败。", "error")
    
    print(f"\n{Colors.OKGREEN}========================================{Colors.ENDC}")
    print(f"{Colors.OKGREEN}[成功] 环境部署完成！{Colors.ENDC}")
    print(f"{Colors.OKGREEN}========================================{Colors.ENDC}")
    print(f"\n{Colors.BOLD}启动应用请运行：{Colors.ENDC}")
    print(f"   {Colors.OKBLUE}uv run main.py{Colors.ENDC}")

if __name__ == "__main__":
    try:
        print_banner()
        phase_0_preflight()
        phase_1_tools()
        phase_2_gpu_config()
        phase_3_install()
        phase_4_check_latex()
        phase_5_verify()
    except KeyboardInterrupt:
        print("\n\n用户取消安装。")
    except Exception as e:
        print(f"\n{Colors.FAIL}[致命错误] {str(e)}{Colors.ENDC}")
    
    input(f"\n{Colors.BOLD}按回车键退出...{Colors.ENDC}")
