from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import shutil
import uuid
from typing import List, Optional, Dict, Any
from math_digitizer.core.generator import ExamGenerator

app = FastAPI()

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

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

class GenerateRequest(BaseModel):
    exam_data: Dict[str, Any]
    title: str = "Math Exam"

@app.get("/api/questions")
async def get_questions():
    bank_file = os.path.join(BANK_DIR, "question_bank.json")
    if not os.path.exists(bank_file):
        return {"questions": []}
    
    try:
        with open(bank_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"questions": data}
            return {"questions": data.get("questions", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
