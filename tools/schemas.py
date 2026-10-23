"""
Pydantic Schemas for Strict Tool Input and Output Validation.
Ensures tool arguments fail cleanly with actionable error messages when malformed.
"""

from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ValidationError


class SearchWebInput(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    max_results: int = Field(5, ge=1, le=20)


class FetchWebpageInput(BaseModel):
    url: str = Field(..., min_length=4)
    max_chars: int = Field(4000, ge=100, le=50000)


class ExecutePythonInput(BaseModel):
    code: str = Field(..., min_length=1)


class SolveMathInput(BaseModel):
    expression: str = Field(..., min_length=1)
    task_type: str = Field("solve")


class CalculateFinanceInput(BaseModel):
    calc_type: str = Field("compound")
    principal: float = Field(..., ge=0)
    rate_pct: float = Field(...)
    time_years: float = Field(..., ge=0)
    n_compounds: int = Field(1, ge=1)


class SqlPlaygroundInput(BaseModel):
    query: str = Field(..., min_length=3)
    csv_path: Optional[str] = None


class ExplainCodeErrorInput(BaseModel):
    code: str = Field(...)
    traceback: str = Field(...)


class ComplexityAnalyzerInput(BaseModel):
    code: str = Field(..., min_length=1)


class LeetcodeCoachInput(BaseModel):
    problem_title: str = Field(..., min_length=1)
    user_attempt: str = Field("")
    hint_level: int = Field(1, ge=1, le=3)


class ResumeImproverInput(BaseModel):
    bullet_point: str = Field(..., min_length=5)
    target_role: str = Field("Software Engineer")


class GitAssistantInput(BaseModel):
    diff_text: str = Field(..., min_length=1)
    task: str = Field("commit_message")


class InterviewEvaluationSchema(BaseModel):
    correctness: int = Field(..., ge=0, le=10)
    clarity: int = Field(..., ge=0, le=10)
    structure: int = Field(..., ge=0, le=10)
    depth: int = Field(..., ge=0, le=10)
    score_range: str = Field(..., min_length=3)
    confidence: str = Field("Medium")


SCHEMA_MAP = {
    "search_web": SearchWebInput,
    "fetch_webpage_content": FetchWebpageInput,
    "execute_python_code": ExecutePythonInput,
    "solve_math": SolveMathInput,
    "solve_math_step_by_step": SolveMathInput,
    "calculate_finance": CalculateFinanceInput,
    "sql_playground": SqlPlaygroundInput,
    "explain_code_error": ExplainCodeErrorInput,
    "complexity_analyzer": ComplexityAnalyzerInput,
    "leetcode_coach": LeetcodeCoachInput,
    "resume_improver": ResumeImproverInput,
    "git_assistant": GitAssistantInput
}


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates arguments against the tool schema.
    Returns (is_valid, parsed_dict, error_message).
    """
    schema_cls = SCHEMA_MAP.get(tool_name)
    if not schema_cls:
        # Schema not strictly enforced for generic tools
        return True, arguments, None

    try:
        validated_obj = schema_cls(**arguments)
        return True, validated_obj.model_dump(), None
    except ValidationError as ve:
        err_msg = "; ".join([f"{e['loc'][0]}: {e['msg']}" for e in ve.errors()])
        return False, None, f"Invalid tool arguments for '{tool_name}': {err_msg}"
