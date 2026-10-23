"""
agents/automl_agent.py — End-to-End AutoML Dashboard & Modeling Agent.

Implements Capability 15:
- Profiles CSV datasets (missing values, types, distributions, outliers).
- Cleans data, applies feature transformations, and prevents test leakage.
- Trains baseline models (Random Forest, Logistic/Ridge, Gradient Boosting).
- Generates interactive comparison charts via tools/chart_generator.py.
- Integrates with background queue for large dataset training.
"""

import os
import logging
from typing import Dict, Any, Optional, Callable

from tools.automl import analyze_data_quality, train_and_compare_models, compute_eda_dashboard_data
from tools.chart_generator import generate_chart
from services.task_queue import default_task_queue

logger = logging.getLogger("chatbot.agents.automl_agent")


class AutoMLAgent:
    def run_automl_pipeline(
        self,
        file_path: str,
        target_column: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end dataset profiling, cleaning, modeling, and chart generation.
        """
        def report(pct: int, msg: str):
            if progress_callback:
                try:
                    progress_callback(pct, msg)
                except Exception:
                    pass

        if not os.path.exists(file_path):
            return {"success": False, "error": f"Dataset file not found: {file_path}"}

        report(10, "Analyzing dataset quality and distributions...")
        quality_res = analyze_data_quality(file_path)

        report(40, "Computing EDA feature distributions...")
        eda_res = compute_eda_dashboard_data(file_path)

        modeling_res = None
        comparison_chart = None

        if target_column:
            report(65, f"Training baseline models for target: '{target_column}'...")
            modeling_res = train_and_compare_models(file_path, target_column)

            # Generate chart comparing models
            if modeling_res.get("success") and "models_compared" in modeling_res:
                models_data = modeling_res["models_compared"]
                names = [m["model"] for m in models_data]
                scores = [m.get("accuracy") or m.get("r2_score") or 0.0 for m in models_data]
                report(85, "Generating interactive model comparison chart...")
                chart_data = {"Model": names, "Score": scores}
                comparison_chart = generate_chart(
                    chart_type="bar",
                    title=f"AutoML Baseline Comparison ({target_column})",
                    data=chart_data,
                    x_label="Model",
                    y_label="Metric Score"
                )

        report(100, "AutoML pipeline complete.")
        return {
            "success": True,
            "data_quality": quality_res,
            "eda_dashboard": eda_res,
            "modeling": modeling_res,
            "comparison_chart": comparison_chart
        }

    def start_automl_job(
        self,
        file_path: str,
        target_column: Optional[str] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Dispatches AutoML pipeline asynchronously."""
        job = default_task_queue.submit_task(
            task_name=f"AutoML: {os.path.basename(file_path)}",
            user_id=user_id,
            func=self.run_automl_pipeline,
            file_path=file_path,
            target_column=target_column
        )
        return {
            "success": True,
            "job_id": job.job_id,
            "status": "queued",
            "message": "AutoML training dispatched to background worker."
        }


default_automl_agent = AutoMLAgent()
