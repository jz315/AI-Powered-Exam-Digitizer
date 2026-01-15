# -*- mode: python ; coding: utf-8 -*-
import os
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

SRC_PATH = os.path.join(SPECPATH, "src")
RUNTIME_HOOKS = [os.path.join(SPECPATH, "runtime_hooks", "stdio_fix.py")]

ctk_datas = collect_data_files("customtkinter")
doclayout_datas = collect_data_files("doclayout_yolo")

project_datas = [
    (os.path.join(SPECPATH, "src", "exam_template.txt"), "src"),
    (os.path.join(SPECPATH, "src", "prompt.md"), "src"),
    (os.path.join(SPECPATH, "src", "prompt_english.md"), "src"),
]

for model_path in glob.glob(os.path.join(SPECPATH, "layout_models", "*.pt")):
    project_datas.append((model_path, "layout_models"))

hiddenimports = [
    "PIL._tkinter_finder",
    "cv2",
    "fitz",
    "jinja2",
    "google.genai",
    "dill",
    "huggingface_hub",
    "gui",
    "gui_app",
    "gui_deps",
    "gui_mixins",
    "gui_ocr",
    "gui_theme",
    "generator",
    "validator",
    "layout_engine",
    "app_paths",
    "image_preprocess",
    "photo_process",
]

hiddenimports += collect_submodules("doclayout_yolo")

a = Analysis(
    ["main.py"],
    pathex=[SPECPATH, SRC_PATH],
    binaries=[],
    datas=ctk_datas + doclayout_datas + project_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=RUNTIME_HOOKS,
    excludes=[
        "notebook",
        "jupyter",
        "IPython",
        "pytest",
        "torch.utils.tensorboard",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MathDigitizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="MathDigitizer",
)
