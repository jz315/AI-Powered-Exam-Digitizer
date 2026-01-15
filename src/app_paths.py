"""
资源路径工具 - 支持 PyInstaller 打包后正确定位资源文件
"""
from pathlib import Path
import sys


def get_app_root() -> Path:
    """获取应用根目录（支持打包和源码运行）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return Path(sys._MEIPASS)
    else:
        # 源码运行
        return Path(__file__).resolve().parent.parent


def get_resource_path(relative_path: str) -> Path:
    """获取资源文件的绝对路径"""
    return get_app_root() / relative_path
