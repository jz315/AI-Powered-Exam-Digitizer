#!/usr/bin/env python3
import subprocess
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "pyi-work"
SPEC_FILE = ROOT / "math_digitizer.spec"
OUTPUT_NAME = "MathDigitizer"


def rmtree_safe(path: Path, retries: int = 3):
    for i in range(retries):
        try:
            if path.exists():
                shutil.rmtree(path)
            return
        except PermissionError:
            if i < retries - 1:
                print(f"权限错误，等待重试... ({i+1}/{retries})")
                time.sleep(2)
            else:
                raise


def clean():
    print("清理旧的构建文件...")
    rmtree_safe(DIST_DIR)
    rmtree_safe(BUILD_DIR)


def check_model():
    model_dir = ROOT / "layout_models"
    models = list(model_dir.glob("*.pt"))
    if not models:
        print("错误: layout_models/ 目录下没有模型文件")
        print("请先运行一次程序让它自动下载，或手动下载模型")
        sys.exit(1)
    print(f"找到模型文件: {[m.name for m in models]}")


def build():
    print("开始构建...")
    result = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath", str(BUILD_DIR),
            "--distpath", str(DIST_DIR),
            str(SPEC_FILE),
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("构建失败!")
        sys.exit(1)


def post_build():
    output_dir = DIST_DIR / OUTPUT_NAME
    if not output_dir.exists():
        print(f"错误: 输出目录不存在 {output_dir}")
        sys.exit(1)
    
    (output_dir / "output").mkdir(exist_ok=True)
    
    print(f"\n构建完成! 输出目录: {output_dir}")
    print(f"可执行文件: {output_dir / 'MathDigitizer.exe'}")


def main():
    clean()
    check_model()
    build()
    post_build()


if __name__ == "__main__":
    main()
