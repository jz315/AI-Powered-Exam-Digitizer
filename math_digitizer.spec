# -*- mode: python ; coding: utf-8 -*-
import os
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

RUNTIME_HOOKS = [os.path.join(SPECPATH, "runtime_hooks", "stdio_fix.py")]

ctk_datas = collect_data_files("customtkinter")
doclayout_datas = collect_data_files("doclayout_yolo")

project_datas = [
    (os.path.join(SPECPATH, "math_digitizer", "resources", "exam_template.txt"), "math_digitizer/resources"),
    (os.path.join(SPECPATH, "math_digitizer", "resources", "prompt.md"), "math_digitizer/resources"),
    (os.path.join(SPECPATH, "math_digitizer", "resources", "prompt_english.md"), "math_digitizer/resources"),
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
    # math_digitizer package
    "math_digitizer",
    "math_digitizer.app_paths",
    "math_digitizer.generator",
    "math_digitizer.validator",
    "math_digitizer.layout_engine",
    "math_digitizer.photo_process",
    # math_digitizer.gui subpackage
    "math_digitizer.gui",
    "math_digitizer.gui.app",
    "math_digitizer.gui.deps",
    "math_digitizer.gui.theme",
    "math_digitizer.gui.ocr",
    # math_digitizer.gui.mixins subpackage
    "math_digitizer.gui.mixins",
    "math_digitizer.gui.mixins.ui",
    "math_digitizer.gui.mixins.pdf_ocr",
    "math_digitizer.gui.mixins.editor",
    "math_digitizer.gui.mixins.log",
    "math_digitizer.gui.mixins.generation",
    "math_digitizer.gui.mixins.status",
    # math_digitizer.tools subpackage
    "math_digitizer.tools",
    "math_digitizer.tools.image_preprocess",
]

hiddenimports += collect_submodules("doclayout_yolo")

a = Analysis(
    ["main.py"],
    pathex=[SPECPATH],
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
