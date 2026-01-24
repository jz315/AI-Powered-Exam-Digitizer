from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from math_digitizer.gui.services.bank_service import BankService, BANK_FILE, BANK_DIR, ASSETS_DIR
from math_digitizer.api.routers.web_settings import get_web_api_key, get_web_config

logger = logging.getLogger("bank")

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class QuestionBase(BaseModel):
    content: str
    type: str = "problem"
    options: Optional[List[str]] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    answer: Optional[str] = None
    analysis: Optional[str] = None
    sub_questions: Optional[List[Dict[str, Any]]] = None
    starred: Optional[bool] = None


class QuestionCreate(QuestionBase):
    id: Optional[str] = None


class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    options: Optional[List[str]] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    answer: Optional[str] = None
    analysis: Optional[str] = None
    sub_questions: Optional[List[Dict[str, Any]]] = None
    starred: Optional[bool] = None


class ImportRequest(BaseModel):
    json_data: str


class ImportResponse(BaseModel):
    success: bool
    message: str
    added: int = 0
    copied: int = 0
    warnings: Optional[List[str]] = None
    warning_count: int = 0


class BulkDeleteRequest(BaseModel):
    ids: List[str]


class GenerateAnswerRequest(BaseModel):
    question_id: str


class GenerateAnswerResponse(BaseModel):
    success: bool
    answer: Optional[str] = None
    analysis: Optional[str] = None
    message: str = ""


class GenerateTagsResponse(BaseModel):
    success: bool
    tags: Optional[List[str]] = None
    difficulty: Optional[str] = None
    message: str = ""


class QuestionResponse(QuestionBase):
    id: str


class GeneratePaperRequest(BaseModel):
    questions: List[Dict[str, Any]] = []
    sections: Optional[List[Dict[str, Any]]] = None
    subject: str = "数学"
    title: Optional[str] = None
    school: Optional[str] = None
    exam_time: Optional[str] = None
    duration: Optional[str] = None


class GeneratePaperResponse(BaseModel):
    success: bool
    message: str = ""
    pdf_path: Optional[str] = None
    tex_path: Optional[str] = None


def load_bank() -> List[Dict[str, Any]]:
    logger.debug(f"Loading bank from {BANK_FILE}")
    if not BANK_FILE.exists():
        logger.warning(f"Bank file not found: {BANK_FILE}")
        return []
    try:
        with open(BANK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                questions = data
            else:
                questions = data.get("questions", [])
            
            for q in questions:
                if "id" in q and not isinstance(q["id"], str):
                    q["id"] = str(q["id"])
            
            logger.info(f"Loaded {len(questions)} questions from bank")
            return questions
    except Exception as e:
        logger.exception(f"Failed to load bank: {e}")
        raise HTTPException(status_code=500, detail="题库文件读取失败，请修复后再操作")


def save_bank(questions: List[Dict[str, Any]]):
    logger.debug(f"Saving {len(questions)} questions to {BANK_FILE}")
    BANK_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    bank_data = {"questions": questions}
    tmp_file = BANK_FILE.with_suffix(".json.tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(bank_data, f, ensure_ascii=False, indent=2)

        if BANK_FILE.exists():
            backup_file = BANK_FILE.with_suffix(".json.bak")
            try:
                shutil.copy2(BANK_FILE, backup_file)
            except Exception:
                pass

        tmp_file.replace(BANK_FILE)
        logger.info(f"Saved {len(questions)} questions to bank")
    except Exception as e:
        logger.exception(f"Failed to save bank: {e}")
        raise HTTPException(status_code=500, detail="题库保存失败，请稍后重试")


def register_bank_routes(app):
    logger.info(f"Registering bank routes, BANK_FILE={BANK_FILE}")
    
    @app.get("/api/questions", response_model=Dict[str, List[QuestionResponse]])
    async def get_questions():
        logger.debug("GET /api/questions called")
        questions = load_bank()
        logger.debug(f"Returning {len(questions)} questions")
        return {"questions": questions}
    
    @app.get("/api/questions/{question_id}", response_model=QuestionResponse)
    async def get_question(question_id: str):
        questions = load_bank()
        for q in questions:
            if q.get("id") == question_id:
                return q
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    
    @app.post("/api/questions", response_model=QuestionResponse, status_code=201)
    async def create_question(question: QuestionCreate):
        logger.info(f"Creating question: type={question.type}, id={question.id}")
        questions = load_bank()
        
        new_id = question.id or f"Q_{uuid.uuid4().hex[:8]}"
        
        existing_ids = {q.get("id") for q in questions}
        if new_id in existing_ids:
            raise HTTPException(status_code=400, detail=f"Question ID {new_id} already exists")
        
        new_question: Dict[str, Any] = {
            "id": new_id,
            "content": question.content,
            "type": question.type,
        }
        
        if question.options is not None:
            new_question["options"] = question.options
        if question.difficulty is not None:
            new_question["difficulty"] = question.difficulty
        if question.tags is not None:
            new_question["tags"] = question.tags
        if question.answer is not None:
            new_question["answer"] = question.answer
        if question.analysis is not None:
            new_question["analysis"] = question.analysis
        if question.sub_questions is not None:
            new_question["sub_questions"] = question.sub_questions
        if question.starred is not None:
            new_question["starred"] = question.starred
        
        questions.append(new_question)
        save_bank(questions)
        logger.info(f"Created question with id={new_id}")
        
        return new_question
    
    @app.put("/api/questions/{question_id}", response_model=QuestionResponse)
    async def update_question(question_id: str, update: QuestionUpdate):
        questions = load_bank()
        
        for i, q in enumerate(questions):
            if q.get("id") == question_id:
                if update.content is not None:
                    q["content"] = update.content
                if update.type is not None:
                    q["type"] = update.type
                if update.options is not None:
                    q["options"] = update.options
                if update.difficulty is not None:
                    q["difficulty"] = update.difficulty
                if update.tags is not None:
                    q["tags"] = update.tags
                if update.answer is not None:
                    q["answer"] = update.answer
                if update.analysis is not None:
                    q["analysis"] = update.analysis
                if update.sub_questions is not None:
                    q["sub_questions"] = update.sub_questions
                if update.starred is not None:
                    q["starred"] = update.starred
                
                questions[i] = q
                save_bank(questions)
                return q
        
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    
    @app.delete("/api/questions/{question_id}")
    async def delete_question(question_id: str):
        logger.info(f"Deleting question: {question_id}")
        questions = load_bank()
        original_count = len(questions)
        
        questions = [q for q in questions if q.get("id") != question_id]
        
        if len(questions) == original_count:
            logger.warning(f"Question not found for delete: {question_id}")
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        save_bank(questions)
        logger.info(f"Deleted question: {question_id}")
        return {"success": True, "message": f"Question {question_id} deleted"}
    
    @app.post("/api/questions/bulk-delete")
    async def bulk_delete_questions(request: BulkDeleteRequest):
        logger.info(f"Bulk deleting {len(request.ids)} questions")
        questions = load_bank()
        ids_to_delete = set(request.ids)
        original_count = len(questions)
        
        questions = [q for q in questions if q.get("id") not in ids_to_delete]
        deleted_count = original_count - len(questions)
        
        save_bank(questions)
        logger.info(f"Bulk deleted {deleted_count} questions")
        return {"success": True, "deleted": deleted_count}
    
    @app.post("/api/questions/import", response_model=ImportResponse)
    async def import_questions(request: ImportRequest):
        logger.info(f"Importing questions, json_data length={len(request.json_data)}")
        service = BankService()
        result = service.import_from_json(request.json_data)
        logger.info(f"Import result: success={result.success}, added={result.added}, copied={result.copied}")
        
        return ImportResponse(
            success=result.success,
            message=result.message,
            added=result.added,
            copied=result.copied,
            warnings=result.warnings or None,
            warning_count=result.warning_count
        )

    @app.post("/api/questions/{question_id}/generate-answer", response_model=GenerateAnswerResponse)
    async def generate_answer(question_id: str):
        logger.info(f"Generating answer for question: {question_id}")
        
        if OpenAI is None:
            return GenerateAnswerResponse(success=False, message="openai 库未安装，请运行 pip install openai")
        
        questions = load_bank()
        question = None
        question_idx = -1
        for i, q in enumerate(questions):
            if q.get("id") == question_id:
                question = q
                question_idx = i
                break
        
        if question is None:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        web_config = get_web_config()
        api_key = get_web_api_key()
        
        if not api_key:
            return GenerateAnswerResponse(success=False, message="未配置 API Key，请在设置中配置")
        
        base_url = web_config.llm.base_url
        model = web_config.llm.model or "deepseek-chat"
        
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            q_type = question.get("type", "problem")
            content = question.get("content", "")
            options = question.get("options", [])
            
            prompt = f"""请解答以下数学题目，给出答案和详细解析。

题目类型：{q_type}
题目内容：{content}
"""
            if options:
                prompt += "\n选项：\n"
                for i, opt in enumerate(options):
                    prompt += f"{chr(65+i)}. {opt}\n"
            
            prompt += """
请按以下JSON格式返回（不要包含其他内容）：
{
  "answer": "答案（选择题只需返回选项字母如A/B/C/D，填空题返回答案，解答题简要写出结果）",
  "analysis": "详细解析过程，使用LaTeX格式书写数学公式，如 $x^2$ 或 $$\\frac{a}{b}$$"
}"""

            logger.debug(f"Calling LLM with model={model}, base_url={base_url}")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位专业的数学教师，擅长解答各类数学题目并给出清晰的解析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            result_text = response.choices[0].message.content or ""
            result_text = result_text.strip()
            logger.debug(f"LLM response: {result_text[:200]}...")
            
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            try:
                result_data = json.loads(result_text)
                answer = result_data.get("answer", "")
                analysis = result_data.get("analysis", "")
            except json.JSONDecodeError:
                answer = ""
                analysis = result_text
            
            question["answer"] = answer
            question["analysis"] = analysis
            questions[question_idx] = question
            save_bank(questions)
            
            logger.info(f"Generated answer for {question_id}: {answer[:50] if answer else 'N/A'}...")
            
            return GenerateAnswerResponse(
                success=True,
                answer=answer,
                analysis=analysis,
                message="生成成功"
            )
            
        except Exception as e:
            logger.exception(f"Failed to generate answer: {e}")
            return GenerateAnswerResponse(success=False, message=f"生成失败: {str(e)}")

    @app.post("/api/questions/{question_id}/generate-tags", response_model=GenerateTagsResponse)
    async def generate_tags(question_id: str):
        logger.info(f"Generating tags for question: {question_id}")
        
        if OpenAI is None:
            return GenerateTagsResponse(success=False, message="openai 库未安装，请运行 pip install openai")
        
        questions = load_bank()
        question = None
        question_idx = -1
        for i, q in enumerate(questions):
            if q.get("id") == question_id:
                question = q
                question_idx = i
                break
        
        if question is None:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
        
        existing_tags = set()
        for q in questions:
            for tag in q.get("tags", []):
                existing_tags.add(tag)
        existing_tags_list = sorted(existing_tags)
        
        web_config = get_web_config()
        api_key = get_web_api_key()
        
        if not api_key:
            return GenerateTagsResponse(success=False, message="未配置 API Key，请在设置中配置")
        
        base_url = web_config.llm.base_url
        model = web_config.llm.model or "deepseek-chat"
        
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            q_type = question.get("type", "problem")
            content = question.get("content", "")
            options = question.get("options", [])
            
            prompt = f"""请为以下数学题目生成合适的标签和难度评估，用于分类和检索。

题目类型：{q_type}
题目内容：{content}
"""
            if options:
                prompt += "\n选项：\n"
                for i, opt in enumerate(options):
                    prompt += f"{chr(65+i)}. {opt}\n"
            
            if existing_tags_list:
                prompt += f"\n已有标签（请优先复用）：{', '.join(existing_tags_list)}\n"
            
            prompt += """
请生成2-5个标签，标签应包含：
1. 知识点（如：函数、导数、三角函数、集合、概率）
2. 题型特征（如：计算题、证明题、应用题）

同时评估题目难度，只能是以下三个值之一：easy（简单）、medium（中等）、hard（困难）

请按以下JSON格式返回（不要包含其他内容）：
{
  "tags": ["标签1", "标签2", "标签3"],
  "difficulty": "easy或medium或hard"
}"""

            logger.debug(f"Calling LLM for tags with model={model}")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位专业的数学教师，擅长对数学题目进行分类和标注。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content or ""
            result_text = result_text.strip()
            logger.debug(f"LLM response for tags: {result_text}")
            
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            try:
                result_data = json.loads(result_text)
                tags = result_data.get("tags", [])
                if not isinstance(tags, list):
                    tags = []
                tags = [str(t).strip() for t in tags if t]
                tags = list(dict.fromkeys(tags))
                
                difficulty = result_data.get("difficulty", "")
                if difficulty not in ("easy", "medium", "hard"):
                    difficulty = None
            except json.JSONDecodeError:
                tags = []
                difficulty = None
            
            if not tags:
                return GenerateTagsResponse(success=False, message="无法解析生成的标签")
            
            current_tags = question.get("tags", []) or []
            merged_tags = list(dict.fromkeys(current_tags + tags))
            
            question["tags"] = merged_tags
            if difficulty:
                question["difficulty"] = difficulty
            questions[question_idx] = question
            save_bank(questions)
            
            logger.info(f"Generated tags for {question_id}: {tags}, difficulty: {difficulty}")
            
            return GenerateTagsResponse(
                success=True,
                tags=merged_tags,
                difficulty=difficulty,
                message=f"生成成功，添加了 {len(tags)} 个标签" + (f"，难度：{difficulty}" if difficulty else "")
            )
            
        except Exception as e:
            logger.exception(f"Failed to generate tags: {e}")
            return GenerateTagsResponse(success=False, message=f"生成失败: {str(e)}")

    @app.post("/api/paper/generate", response_model=GeneratePaperResponse)
    async def generate_paper(request: GeneratePaperRequest):
        logger.info(f"Generating paper with {len(request.questions)} questions, {len(request.sections or [])} sections")
        
        from math_digitizer.core.generator import ExamGenerator
        import tempfile
        from datetime import datetime
        
        try:
            if request.sections:
                sections = request.sections
            else:
                type_order = {"single_choice": 1, "multiple_choice": 2, "fill": 3, "problem": 4}
                type_labels = {
                    "single_choice": "选择题",
                    "multiple_choice": "多选题", 
                    "fill": "填空题",
                    "problem": "解答题"
                }
                
                sections_dict: Dict[str, List[Dict[str, Any]]] = {}
                for q in request.questions:
                    q_type = q.get("type", "problem")
                    if q_type not in sections_dict:
                        sections_dict[q_type] = []
                    sections_dict[q_type].append(q)
                
                sections = []
                for q_type in sorted(sections_dict.keys(), key=lambda t: type_order.get(t, 99)):
                    sections.append({
                        "title": type_labels.get(q_type, q_type),
                        "type": q_type,
                        "questions": sections_dict[q_type]
                    })
            
            paper_data = {
                "meta": {
                    "title": request.title,
                    "school": request.school,
                    "exam_time": request.exam_time,
                    "duration": request.duration,
                    "subject": request.subject,
                    "generated_at": datetime.now().isoformat()
                },
                "sections": sections
            }
            
            output_dir = BANK_DIR / "generated"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tex_path = output_dir / f"paper_{timestamp}.tex"
            
            generator = ExamGenerator()
            processed = generator.process_data(json.dumps(paper_data))
            
            if not processed:
                return GeneratePaperResponse(success=False, message="处理试卷数据失败")
            
            tex_file = generator.render(processed, str(tex_path))
            
            if not tex_file:
                return GeneratePaperResponse(success=False, message="生成 LaTeX 文件失败")
            
            compile_success = generator.compile_pdf(tex_file)
            
            pdf_path = str(tex_path).replace(".tex", ".pdf") if compile_success else None
            
            logger.info(f"Paper generated: tex={tex_file}, pdf={pdf_path}")
            
            pdf_exists = pdf_path is not None and Path(pdf_path).exists()
            
            return GeneratePaperResponse(
                success=True,
                message="试卷生成成功" + (" (PDF编译成功)" if compile_success else " (PDF编译失败，请检查xelatex是否安装)"),
                tex_path=str(tex_path),
                pdf_path=pdf_path if compile_success and pdf_exists else None
            )
            
        except Exception as e:
            logger.exception(f"Failed to generate paper: {e}")
            return GeneratePaperResponse(success=False, message=f"生成失败: {str(e)}")
