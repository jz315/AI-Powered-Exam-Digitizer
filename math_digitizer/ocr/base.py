import os
from pathlib import Path
from typing import Optional

from math_digitizer.utils.paths import get_resource_path
from math_digitizer.config import get_config, get_api_key, SecretKey

DEFAULT_LAYOUT_MODEL = "doclayout_yolo"
LAYOUT_MODEL_LABELS = {
    "doclayout_yolo": "DocLayout-YOLO (DocStructBench 1280)",
    "pp_doclayout_plus_l": "PP-DocLayout_plus-L (PaddleOCR)",
    "deepseek_ocr": "Deepseek OCR (Layout Only)",
    "auto_router": "Auto (DocLayout->Deepseek if missed)",
}

MODEL_FILENAME = "doclayout_yolo_docstructbench_imgsz1280_2501.pt"
MODEL_DIR = get_resource_path("layout_models")
HF_REPO_ID = "juliozhao/DocLayout-YOLO-DocStructBench-imgsz1280-2501"


def _resolve_deepseek_base_url(explicit_base_url: Optional[str]) -> str:
    if explicit_base_url:
        return explicit_base_url
    
    config = get_config()
    if config.deepseek.provider == "siliconflow":
        return "https://api.siliconflow.cn/v1"
    if config.deepseek.base_url:
        return config.deepseek.base_url
    
    provider = (os.getenv("DEEPSEEK_OCR_PROVIDER", "") or "").strip().lower()
    if provider == "siliconflow":
        return "https://api.siliconflow.cn/v1"
    env_base_url = (os.getenv("DEEPSEEK_OCR_BASE_URL", "") or "").strip()
    if env_base_url:
        return env_base_url
    return "https://api.modelverse.cn/v1/"


def ensure_model_exists() -> Path:
    model_path = MODEL_DIR / MODEL_FILENAME

    if model_path.exists():
        return model_path

    print(f"模型文件不存在，尝试从 HuggingFace 下载: {MODEL_FILENAME}")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download

        downloaded_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=MODEL_FILENAME,
            local_dir=str(MODEL_DIR),
        )
        print(f"模型下载完成: {downloaded_path}")
        return Path(downloaded_path)
    except Exception as e:
        raise RuntimeError(
            f"""无法下载模型文件: {e}

请手动下载模型:
  1. 访问 https://huggingface.co/{HF_REPO_ID}
  2. 下载 {MODEL_FILENAME}
  3. 放到 {MODEL_DIR}/ 目录下"""
        ) from e


def layout_model_label_from_key(key: str) -> str:
    return LAYOUT_MODEL_LABELS.get(key, key)


def layout_model_key_from_label(label: str) -> str:
    for key, value in LAYOUT_MODEL_LABELS.items():
        if value == label:
            return key
    return label


def create_layout_extractor(
    model_key: str,
    deepseek_api_key: Optional[str] = None,
    deepseek_base_url: Optional[str] = None,
    deepseek_model: Optional[str] = None,
    auto_router_config: Optional[dict] = None,
):
    if model_key == "pp_doclayout_plus_l":
        from math_digitizer.ocr.extractors.paddle import PPDocLayoutPlusExtractor

        return PPDocLayoutPlusExtractor()
    if model_key == "deepseek_ocr":
        from math_digitizer.ocr.extractors.deepseek import DeepseekOcrLayoutExtractor

        kwargs = {}
        if deepseek_api_key:
            kwargs["api_key"] = deepseek_api_key
        if deepseek_base_url:
            kwargs["base_url"] = deepseek_base_url
        if deepseek_model:
            kwargs["model"] = deepseek_model
        return DeepseekOcrLayoutExtractor(**kwargs)
    if model_key == "auto_router":
        from math_digitizer.ocr.extractors.auto_router import AutoRouterLayoutExtractor

        kwargs = {}
        if deepseek_api_key:
            kwargs["api_key"] = deepseek_api_key
        if deepseek_base_url:
            kwargs["base_url"] = deepseek_base_url
        if deepseek_model:
            kwargs["model"] = deepseek_model
        return AutoRouterLayoutExtractor(deepseek_kwargs=kwargs, **(auto_router_config or {}))

    from math_digitizer.ocr.extractors.yolo import DocLayoutExtractor

    return DocLayoutExtractor()


def parse_page_range(page_range: str, max_pages: int) -> list[int]:
    if not page_range:
        return list(range(max_pages))
    page_range = page_range.replace(" ", "")
    if not page_range:
        return list(range(max_pages))

    pages: set[int] = set()
    parts = [p for p in page_range.split(",") if p]
    for part in parts:
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left) if left else 1
            end = int(right) if right else max_pages
        else:
            start = end = int(part)

        if start < 1:
            start = 1
        if end > max_pages:
            end = max_pages
        if end < start:
            continue
        for p in range(start, end + 1):
            pages.add(p - 1)

    return sorted(pages)
