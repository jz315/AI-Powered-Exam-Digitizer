from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from math_digitizer.core.validator import validate_json_and_latex, ValidationIssue

# --- Models ---

class ValidateRequest(BaseModel):
    json_content: str

class ValidationIssueModel(BaseModel):
    line: int
    message: str
    severity: str  # "error" or "warning"

class ValidateResponse(BaseModel):
    is_valid: bool
    issues: List[ValidationIssueModel]

# --- API Routes ---

def register_validate_routes(app):
    
    @app.post("/api/validate", response_model=ValidateResponse)
    async def validate_json(request: ValidateRequest):
        """Validate JSON structure for the exam schema."""
        try:
            # 1. Syntax Check
            try:
                # We don't really need the parsed object, just checking syntax
                _ = json.loads(request.json_content)
            except json.JSONDecodeError as e:
                return {
                    "is_valid": False,
                    "issues": [{
                        "line": e.lineno,
                        "message": f"JSON Syntax Error: {e.msg}",
                        "severity": "error"
                    }]
                }

            # 2. Schema/Structure Validation
            # Utilizing the existing core validator
            _, issues = validate_json_and_latex(request.json_content)
            
            response_issues = []
            has_error = False
            for issue in issues:
                if issue.severity == "error":
                    has_error = True
                response_issues.append({
                    "line": issue.line or 0,
                    "message": issue.message,
                    "severity": issue.severity
                })
            
            return {
                "is_valid": not has_error,
                "issues": response_issues
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
