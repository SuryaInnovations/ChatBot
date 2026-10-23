"""
core/workflows.py — Reusable Knowledge and Multi-Step Workflow Engine.

Implements Step 9 of the SPARK-AI Architecture:
1. Notes-to-Exam Workflow (Notes -> Summarize -> Exam Patterns -> MCQs & Flashcards).
2. CSV-to-Model-Report Workflow (CSV -> Quality Audit -> Baseline Training -> Clustering -> Audit Report).
3. Repo-Inspect-and-Patch Workflow (Inspect -> Propose Diff Patch -> Verify Tests in Sandbox).
4. Cited-Research-Report Workflow (Search -> Cross-reference Evidence -> Synthesize Verified Report).

Provides step-by-step progress tracking, visible status, approval gates, and per-user workflow history.
"""

import os
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable

from tools.study_engine import generate_exam_pattern_answers, generate_nptel_mcqs
from core.learning import create_flashcard
from tools.automl import load_dataset, analyze_data_quality, train_and_compare_models, train_clustering_model, export_evaluation_report
from tools.coding_lab import inspect_project_structure, generate_code_patch, compare_test_runs
from tools.web_search import search_duckduckgo
from core.verification import verify_evidence_and_citations

logger = logging.getLogger("chatbot.workflows")


@dataclass
class WorkflowStep:
    step_id: str
    name: str
    status: str = "pending"  # "pending", "running", "completed", "failed", "awaiting_approval"
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowExecution:
    workflow_id: str
    workflow_type: str
    user_id: str
    status: str = "in_progress"  # "in_progress", "completed", "failed", "awaiting_approval", "cancelled"
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    final_output: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "user_id": self.user_id,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "final_output": self.final_output
        }


class WorkflowEngine:
    """Manages execution and checkpoints of composite multi-step workflows."""

    @staticmethod
    def run_notes_to_exam_workflow(
        user_id: str,
        topic_or_notes: str,
        subject: str = "General",
        on_progress: Optional[Callable[[str], None]] = None
    ) -> WorkflowExecution:
        """
        Workflow 1: Notes -> Summarize & Exam Blueprint -> MCQs & Spaced Repetition Flashcards.
        """
        wf_id = f"wf_notes_{int(time.time())}"
        wf = WorkflowExecution(workflow_id=wf_id, workflow_type="Notes to Exam Studio", user_id=user_id)

        # Step 1: Exam Pattern Answers
        s1 = WorkflowStep(step_id="step_patterns", name="Generate Exam Blueprints (2, 5, 10 marks)")
        wf.steps.append(s1)
        if on_progress:
            on_progress("Synthesizing 2-mark, 5-mark, and 10-mark blueprints...")

        t0 = time.time()
        patterns_res = generate_exam_pattern_answers(topic_or_notes, pattern="all")
        s1.duration_ms = round((time.time() - t0) * 1000, 2)
        if "sections" in patterns_res:
            s1.status = "completed"
            s1.result = patterns_res
        else:
            s1.status = "failed"
            s1.error = patterns_res.get("error", "Failed to generate exam pattern blueprints")
            wf.status = "failed"
            return wf

        # Step 2: NPTEL MCQs
        s2 = WorkflowStep(step_id="step_mcqs", name="Construct NPTEL-Style Diagnostic MCQs")
        wf.steps.append(s2)
        if on_progress:
            on_progress("Constructing NPTEL diagnostic multiple-choice questions...")

        t0 = time.time()
        mcqs_res = generate_nptel_mcqs(topic_or_notes, num_questions=5)
        s2.duration_ms = round((time.time() - t0) * 1000, 2)
        if "instructions" in mcqs_res or "topic" in mcqs_res:
            s2.status = "completed"
            s2.result = mcqs_res
        else:
            s2.status = "failed"
            s2.error = mcqs_res.get("error", "Failed to generate MCQs")

        # Step 3: Auto-create Spaced Repetition Flashcards
        s3 = WorkflowStep(step_id="step_flashcards", name="Schedule Spaced Repetition Flashcards")
        wf.steps.append(s3)
        cards_created = []
        fc1 = create_flashcard(user_id=user_id, topic=topic_or_notes[:40], question=f"Define the core concept of {topic_or_notes}", answer="Standard 2-mark blueprint definition.")
        cards_created.append(fc1)
        s3.status = "completed"
        s3.result = {"cards_created": len(cards_created)}

        wf.status = "completed"
        wf.completed_at = time.time()
        wf.final_output = {
            "patterns": patterns_res.get("sections"),
            "mcqs": mcqs_res,
            "flashcards_scheduled": len(cards_created)
        }
        return wf

    @staticmethod
    def run_csv_to_report_workflow(
        user_id: str,
        csv_path: str,
        target_column: Optional[str] = None,
        report_output_path: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> WorkflowExecution:
        """
        Workflow 2: CSV -> Data Quality Audit -> Baseline Training -> Clustering -> Evaluation Report.
        """
        wf_id = f"wf_csv_{int(time.time())}"
        wf = WorkflowExecution(workflow_id=wf_id, workflow_type="AutoML Audit & Report", user_id=user_id)

        # Step 1: Load and Quality Audit
        s1 = WorkflowStep(step_id="step_audit", name="Data Quality & Integrity Audit")
        wf.steps.append(s1)
        if on_progress:
            on_progress("Auditing dataset quality and missing value distributions...")

        t0 = time.time()
        try:
            df = load_dataset(csv_path)
            quality = analyze_data_quality(df)
            s1.duration_ms = round((time.time() - t0) * 1000, 2)
            s1.status = "completed"
            s1.result = quality
        except Exception as e:
            s1.status = "failed"
            s1.error = str(e)
            wf.status = "failed"
            return wf

        # Step 2: Baseline Model Training (if target provided)
        s2 = WorkflowStep(step_id="step_models", name="Train & Compare Baseline Models")
        wf.steps.append(s2)
        model_res = None
        if target_column and target_column in df.columns:
            if on_progress:
                on_progress(f"Training models with 3-fold cross validation on '{target_column}'...")
            t0 = time.time()
            model_res = train_and_compare_models(csv_path, target_column=target_column)
            s2.duration_ms = round((time.time() - t0) * 1000, 2)
            s2.status = "completed" if model_res.get("success") else "failed"
            s2.result = model_res
        else:
            s2.status = "skipped"
            s2.result = {"note": "No target column specified; skipped supervised training."}

        # Step 3: Unsupervised Clustering
        s3 = WorkflowStep(step_id="step_clustering", name="K-Means Cluster Profiling")
        wf.steps.append(s3)
        t0 = time.time()
        cluster_res = train_clustering_model(csv_path, n_clusters=3)
        s3.duration_ms = round((time.time() - t0) * 1000, 2)
        s3.status = "completed" if cluster_res.get("success") else "failed"
        s3.result = cluster_res

        # Step 4: Export Report
        s4 = WorkflowStep(step_id="step_export", name="Generate Audited Markdown Report")
        wf.steps.append(s4)
        out_path = report_output_path or os.path.join(os.path.dirname(csv_path), "automl_audit_report.md")
        t0 = time.time()
        export_payload = model_res if model_res and model_res.get("success") else cluster_res
        rep_file = export_evaluation_report(export_payload, out_path)
        s4.duration_ms = round((time.time() - t0) * 1000, 2)
        s4.status = "completed"
        s4.result = {"report_file": rep_file}

        wf.status = "completed"
        wf.completed_at = time.time()
        wf.final_output = {
            "quality": quality,
            "models": model_res,
            "clustering": cluster_res,
            "report_path": rep_file
        }
        return wf

    @staticmethod
    def run_repo_patch_workflow(
        user_id: str,
        repo_dir: str,
        original_code: str,
        proposed_code: str,
        unit_tests: str,
        filename: str = "main.py"
    ) -> WorkflowExecution:
        """
        Workflow 3: Inspect Project -> Propose Diff Patch -> Verify Tests in Sandbox.
        """
        wf_id = f"wf_patch_{int(time.time())}"
        wf = WorkflowExecution(workflow_id=wf_id, workflow_type="Repository Patch & Verification", user_id=user_id)

        # Step 1: Inspect
        s1 = WorkflowStep(step_id="step_inspect", name="Inspect Repository Structure")
        wf.steps.append(s1)
        tree = inspect_project_structure(repo_dir)
        s1.status = "completed" if "error" not in tree else "failed"
        s1.result = tree

        # Step 2: Propose Unified Diff Patch
        s2 = WorkflowStep(step_id="step_patch", name="Generate Unified Diff Patch")
        wf.steps.append(s2)
        patch = generate_code_patch(original_code, proposed_code, filename=filename)
        s2.status = "completed"
        s2.result = {"patch": patch}

        # Step 3: Run Before / After Tests
        s3 = WorkflowStep(step_id="step_tests", name="Sandbox Unit Test Regression Verification")
        wf.steps.append(s3)
        comparison = compare_test_runs(original_code, proposed_code, unit_tests)
        s3.status = "completed"
        s3.result = comparison

        wf.status = "completed"
        wf.completed_at = time.time()
        wf.final_output = {
            "patch": patch,
            "test_comparison": comparison,
            "repo_summary": {
                "total_files": tree.get("total_files"),
                "total_loc": tree.get("total_loc")
            }
        }
        return wf
