import os
import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

from math_digitizer.ocr import (
    create_layout_extractor,
    DEFAULT_LAYOUT_MODEL,
    layout_model_key_from_label,
    parse_page_range,
)
from math_digitizer.config import get_config, save_config
from math_digitizer.api.routers.web_settings import get_web_api_key_by_type

logger = logging.getLogger("ocr_api")

# Thread pool for CPU-bound OCR tasks
_ocr_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr_worker")

# --- Models ---

class OcrJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class OcrStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    result: Optional[str] = None
    error: Optional[str] = None
    preview_url: Optional[str] = None

class OcrConfig(BaseModel):
    layout_model: str = "doclayout_yolo"
    ocr_engine: str = "gemini"
    ocr_model: str = "gemini-2.0-flash"
    page_range: str = ""
    dpi: int = 200
    deepseek_provider: str = "modelverse"
    deepseek_base_url: str = ""
    router_mode: str = "any"
    outside_ratio: float = 0.01
    min_text_ratio: float = 0.0005
    gemini_probe: bool = False
    gemini_probe_model: str = "gemini-2.5-flash-lite"

# --- In-Memory Job Store ---
ocr_jobs: Dict[str, Dict[str, Any]] = {}

# --- Helper Functions ---

def _get_deepseek_base_url(provider: str, custom_url: str) -> str:
    if provider == "siliconflow":
        return "https://api.siliconflow.cn/v1"
    if provider == "custom" and custom_url:
        return custom_url
    return "https://api.modelverse.cn/v1/"

def _run_layout_analysis(
    pdf_path: Path,
    output_dir: Path,
    layout_model: str,
    page_range_str: str,
    dpi: int,
    deepseek_key: Optional[str],
    deepseek_base_url: Optional[str],
    auto_router_config: Optional[dict],
) -> List[dict]:
    """Run layout analysis synchronously in thread pool."""
    import fitz
    
    doc = fitz.open(str(pdf_path))
    max_pages = len(doc)
    doc.close()
    
    pages = parse_page_range(page_range_str, max_pages) if page_range_str else list(range(max_pages))
    
    extractor = create_layout_extractor(
        model_key=layout_model,
        deepseek_api_key=deepseek_key,
        deepseek_base_url=deepseek_base_url,
        auto_router_config=auto_router_config,
    )
    
    all_items = []
    doc = fitz.open(str(pdf_path))
    
    for page_idx in pages:
        if page_idx >= len(doc):
            continue
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=dpi)
        img_path = output_dir / f"page_{page_idx + 1:04d}.png"
        pix.save(str(img_path))
        
        items = extractor.extract(str(img_path))
        for item in items:
            item["page"] = page_idx + 1
            item["image_path"] = str(img_path)
        all_items.extend(items)
    
    doc.close()
    return all_items

def _run_ocr_on_items(
    items: List[dict],
    output_dir: Path,
    ocr_engine: str,
    ocr_model: str,
    ocr_api_key: str,
    progress_callback=None,
) -> str:
    """Run OCR on extracted items and return merged text."""
    from math_digitizer.gui.widgets.ocr_widget import call_ocr
    from math_digitizer.gui.services.prompt_service import PromptService
    from PIL import Image
    
    prompt_service = PromptService()
    prompt = prompt_service.get_prompt()
    
    results = []
    total = len(items)
    
    for idx, item in enumerate(items):
        label = item.get("label", "").lower()
        if label in ["title", "header", "footer", "page_no", "abandon"]:
            continue
        
        bbox = item.get("bbox") or item.get("box")
        if not bbox:
            continue
        
        img_path = item.get("image_path")
        if not img_path or not os.path.exists(img_path):
            continue
        
        try:
            img = Image.open(img_path)
            x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
            crop = img.crop((x1, y1, x2, y2))
            crop_path = output_dir / f"crop_{idx:04d}.png"
            crop.save(str(crop_path))
            
            ocr_text = call_ocr(
                image_path=str(crop_path),
                provider=ocr_engine,
                api_key=ocr_api_key,
                model=ocr_model,
                prompt=prompt,
            )
            
            if ocr_text and ocr_text.strip():
                results.append(f"<!-- Page {item.get('page', '?')}, {label} -->\n{ocr_text.strip()}")
        except Exception as e:
            logger.warning(f"OCR failed for item {idx}: {e}")
        
        if progress_callback:
            progress_callback(50 + int(45 * (idx + 1) / max(total, 1)))
    
    return "\n\n".join(results)

async def process_ocr_task(
    job_id: str,
    file_path: str,
    config: OcrConfig,
):
    """Background task to run OCR processing."""
    loop = asyncio.get_event_loop()
    
    try:
        ocr_jobs[job_id]["status"] = "processing"
        ocr_jobs[job_id]["progress"] = 5
        logger.info(f"Starting OCR job {job_id} with model={config.layout_model}, engine={config.ocr_engine}")
        
        output_dir = Path("output") / "web_uploads" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        deepseek_key_type = f"deepseek_{config.deepseek_provider}"
        deepseek_key = get_web_api_key_by_type(deepseek_key_type)
        deepseek_base_url = _get_deepseek_base_url(config.deepseek_provider, config.deepseek_base_url)
        
        auto_router_config = None
        if config.layout_model == "auto_router":
            auto_router_config = {
                "router_mode": config.router_mode,
                "outside_ratio_thresh": config.outside_ratio,
                "min_text_ratio": config.min_text_ratio,
                "use_gemini_probe": config.gemini_probe,
                "gemini_probe_model": config.gemini_probe_model,
            }
        
        ocr_jobs[job_id]["progress"] = 10
        
        items = await loop.run_in_executor(
            _ocr_executor,
            _run_layout_analysis,
            Path(file_path),
            output_dir,
            config.layout_model,
            config.page_range,
            config.dpi,
            deepseek_key,
            deepseek_base_url,
            auto_router_config,
        )
        
        ocr_jobs[job_id]["progress"] = 50
        logger.info(f"Layout analysis complete for {job_id}: {len(items)} items")
        
        if config.ocr_engine == "gemini":
            ocr_api_key = get_web_api_key_by_type("gemini")
        elif config.ocr_engine == "aliyun":
            ocr_api_key = get_web_api_key_by_type("aliyun")
        else:
            ocr_api_key = None
        
        if not ocr_api_key:
            ocr_jobs[job_id]["status"] = "error"
            ocr_jobs[job_id]["error"] = f"未配置 {config.ocr_engine.upper()} API Key，请在设置页面配置"
            return
        
        def update_progress(p):
            ocr_jobs[job_id]["progress"] = p
        
        merged_text = await loop.run_in_executor(
            _ocr_executor,
            _run_ocr_on_items,
            items,
            output_dir,
            config.ocr_engine,
            config.ocr_model,
            ocr_api_key,
            update_progress,
        )
        
        ocr_jobs[job_id]["progress"] = 100
        ocr_jobs[job_id]["status"] = "completed"
        ocr_jobs[job_id]["result"] = merged_text or "OCR 完成，但未识别到文本内容"
        logger.info(f"OCR job {job_id} completed, result length: {len(merged_text)}")
        
    except Exception as e:
        logger.exception(f"OCR job {job_id} failed: {e}")
        ocr_jobs[job_id]["status"] = "error"
        ocr_jobs[job_id]["error"] = str(e)
    finally:
        pass

# --- API Routes ---

def register_ocr_routes(app):
    
    @app.post("/api/ocr/upload-pdf", response_model=OcrJobResponse)
    async def upload_pdf(
        file: UploadFile = File(...),
        layout_model: str = Form("doclayout_yolo"),
        ocr_engine: str = Form("gemini"),
        ocr_model: str = Form("gemini-2.0-flash"),
        page_range: str = Form(""),
        dpi: int = Form(200),
        deepseek_provider: str = Form("modelverse"),
        deepseek_base_url: str = Form(""),
        router_mode: str = Form("any"),
        outside_ratio: float = Form(0.01),
        min_text_ratio: float = Form(0.0005),
        gemini_probe: bool = Form(False),
        gemini_probe_model: str = Form("gemini-2.5-flash-lite"),
        background_tasks: BackgroundTasks = BackgroundTasks()
    ):
        job_id = str(uuid.uuid4())
        
        upload_dir = Path("temp_uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / f"{job_id}_{file.filename}"
        
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        
        ocr_jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "result": None,
            "error": None
        }
        
        config = OcrConfig(
            layout_model=layout_model,
            ocr_engine=ocr_engine,
            ocr_model=ocr_model,
            page_range=page_range,
            dpi=dpi,
            deepseek_provider=deepseek_provider,
            deepseek_base_url=deepseek_base_url,
            router_mode=router_mode,
            outside_ratio=outside_ratio,
            min_text_ratio=min_text_ratio,
            gemini_probe=gemini_probe,
            gemini_probe_model=gemini_probe_model,
        )
        
        background_tasks.add_task(
            process_ocr_task, 
            job_id, 
            str(file_path), 
            config,
        )
        
        logger.info(f"OCR job {job_id} queued for {file.filename}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "PDF uploaded and OCR job started."
        }

    @app.get("/api/ocr/status/{job_id}", response_model=OcrStatusResponse)
    async def get_ocr_status(job_id: str):
        if job_id not in ocr_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job = ocr_jobs[job_id]
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "result": job.get("result"),
            "error": job.get("error"),
            "preview_url": job.get("preview_url"),
        }
