from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import shutil
import uuid
import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Dict, Any
from math_digitizer.core.generator import ExamGenerator
from math_digitizer.api.routers.ocr import register_ocr_routes
from math_digitizer.api.routers.validate import register_validate_routes
from math_digitizer.api.routers.settings import register_settings_routes
from math_digitizer.api.routers.bank import register_bank_routes
from math_digitizer.api.routers.web_settings import register_web_settings_routes

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"),
    ]
)
logger = logging.getLogger("server")
logger.info(f"Logging to {LOG_FILE}")

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f">>> {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"<<< {request.method} {request.url.path} -> {response.status_code}")
        return response
    except Exception as e:
        logger.exception(f"!!! {request.method} {request.url.path} -> Exception: {e}")
        raise

register_ocr_routes(app)
register_validate_routes(app)
register_settings_routes(app)
register_bank_routes(app)
register_web_settings_routes(app)

logger.info("Routes registered: OCR, Validate, Settings, Bank, WebSettings")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.join(BASE_DIR, "output", "question_bank")
ASSETS_DIR = os.path.join(BANK_DIR, "assets")
GENERATED_DIR = os.path.join(BASE_DIR, "output", "generated_exams")

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR, exist_ok=True)

if not os.path.exists(GENERATED_DIR):
    os.makedirs(GENERATED_DIR, exist_ok=True)

GENERATED_PAPERS_DIR = os.path.join(BANK_DIR, "generated")
if not os.path.exists(GENERATED_PAPERS_DIR):
    os.makedirs(GENERATED_PAPERS_DIR, exist_ok=True)

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/output/question_bank/generated", StaticFiles(directory=GENERATED_PAPERS_DIR), name="generated_papers")


class GenerateRequest(BaseModel):
    exam_data: Dict[str, Any]
    title: str = "Math Exam"


@app.post("/api/generate-pdf")
async def generate_pdf(request: GenerateRequest):
    try:
        exam_dict = request.exam_data
        
        if "meta" not in exam_dict:
            exam_dict["meta"] = {}
        if "title" not in exam_dict["meta"]:
            exam_dict["meta"]["title"] = request.title

        build_id = str(uuid.uuid4())
        build_dir = os.path.join(GENERATED_DIR, build_id)
        os.makedirs(build_dir, exist_ok=True)
        
        build_assets_dir = os.path.join(build_dir, "assets")
        if os.path.exists(ASSETS_DIR):
            shutil.copytree(ASSETS_DIR, build_assets_dir)
        else:
            os.makedirs(build_assets_dir, exist_ok=True)

        generator = ExamGenerator()
        
        exam_json_str = json.dumps(exam_dict)
        processed_data = generator.process_data(exam_json_str)
        
        generator.replace_inline_images(
            processed_data, 
            asset_dir=build_assets_dir
        )

        output_tex = os.path.join(build_dir, "exam.tex")
        generator.render(processed_data, output_tex=output_tex)
        
        success = generator.compile_pdf(output_tex)
        
        pdf_path = os.path.join(build_dir, "exam.pdf")
        if not os.path.exists(pdf_path):
             raise HTTPException(status_code=500, detail="PDF compilation failed completely. LaTeX errors prevented output.")

        return FileResponse(
            pdf_path, 
            filename=f"{request.title.replace(' ', '_')}.pdf",
            media_type="application/pdf"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
