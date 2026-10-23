"""
workflows/templates.py — One-Click Reusable Guided Workflows.

Provides pre-packaged multi-step workflows:
- "study_quiz": Topic explanation -> flashcard generation -> practice quiz.
- "bug_diagnosis": Traceback inspection -> root cause analysis -> patch diff preview -> test run.
- "csv_analysis": Data profiling -> cleaning -> correlation analysis -> baseline AutoML.
- "research_report": Subquestion planning -> web search -> citation verification -> Markdown/PDF export.
"""

from typing import Dict, Any, List

WORKFLOW_TEMPLATES = {
    "study_quiz": {
        "title": "Interactive Study & Quiz Workflow",
        "description": "Explains a topic in depth and immediately generates interactive MCQs and flashcards.",
        "steps": [
            {"step": 1, "tool": "study_explain", "action": "Generate intuitive conceptual breakdown"},
            {"step": 2, "tool": "generate_quiz_flashcards", "action": "Create flashcards for active recall"},
            {"step": 3, "tool": "generate_nptel_mcqs", "action": "Produce 5 exam-pattern practice questions"}
        ]
    },
    "bug_diagnosis": {
        "title": "Bug Diagnosis & Safe Patching",
        "description": "Analyzes an error traceback, inspects code, proposes a unified diff, and verifies with tests.",
        "steps": [
            {"step": 1, "tool": "explain_code_error", "action": "Identify error root cause"},
            {"step": 2, "tool": "coding_propose_diff", "action": "Generate unified diff preview"},
            {"step": 3, "tool": "run_sandbox_tests", "action": "Verify fix passes tests in sandbox"},
            {"step": 4, "tool": "apply_patch", "action": "Apply patch and record version snapshot"}
        ]
    },
    "csv_analysis": {
        "title": "Automated CSV EDA & AutoML",
        "description": "Profiles uploaded dataset, identifies data issues, computes distributions, and trains baselines.",
        "steps": [
            {"step": 1, "tool": "analyze_data_quality", "action": "Check missing values and column types"},
            {"step": 2, "tool": "compute_eda_dashboard_data", "action": "Generate feature distributions"},
            {"step": 3, "tool": "train_and_compare_models", "action": "Train baseline ML models"},
            {"step": 4, "tool": "generate_chart", "action": "Produce interactive Plotly performance chart"}
        ]
    },
    "research_report": {
        "title": "Deep Research & Verified Report",
        "description": "Plans inquiry angles, searches web sources, extracts evidence, and compiles a sourced report.",
        "steps": [
            {"step": 1, "tool": "deep_research", "action": "Gather multi-source web evidence"},
            {"step": 2, "tool": "verify_evidence_citations", "action": "Validate claim-source alignment"},
            {"step": 3, "tool": "document_generator", "action": "Compile and download report in PDF or Markdown"}
        ]
    }
}


def get_workflow_template(workflow_id: str) -> Dict[str, Any]:
    return WORKFLOW_TEMPLATES.get(workflow_id.lower(), WORKFLOW_TEMPLATES["study_quiz"])


def list_workflows() -> List[Dict[str, Any]]:
    return [{"id": k, **v} for k, v in WORKFLOW_TEMPLATES.items()]
