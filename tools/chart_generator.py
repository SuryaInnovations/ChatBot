"""
tools/chart_generator.py — Interactive Plotly & Matplotlib Chart Generation.

Implements Capability 12 (Charts):
- Generates interactive HTML charts via Plotly (bar, line, scatter, pie, histogram, heatmap).
- Generates publication-ready static PNG images.
- Registers charts into default_artifact_service.
- Returns HTML snippets and image paths for UI rendering.
"""

import os
import uuid
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

from services.artifact_service import default_artifact_service

logger = logging.getLogger("chatbot.tools.chart_generator")


def generate_chart(
    chart_type: str,
    title: str,
    data: Dict[str, Any],  # {"x": [...], "y": [...]} or records
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    user_id: str = "default_user",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates an interactive Plotly chart or Matplotlib plot and saves it as an artifact.
    Supported chart types: 'bar', 'line', 'scatter', 'pie', 'histogram'.
    """
    chart_type = chart_type.lower().strip()
    clean_title = title.strip() or "Generated Chart"
    df = pd.DataFrame(data)

    try:
        import plotly.express as px
        fig = None
        cols = list(df.columns)

        x_col = cols[0] if cols else "x"
        y_col = cols[1] if len(cols) > 1 else cols[0]

        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=clean_title)
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=clean_title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=clean_title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col if len(cols) > 1 else None, title=clean_title)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_col, title=clean_title)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=clean_title)

        if x_label and hasattr(fig, "update_xaxes"):
            fig.update_xaxes(title_text=x_label)
        if y_label and hasattr(fig, "update_yaxes"):
            fig.update_yaxes(title_text=y_label)

        # Generate standalone HTML snippet
        html_str = fig.to_html(full_html=False, include_plotlyjs="cdn")
        html_fname = f"chart_{chart_type}_{uuid.uuid4().hex[:6]}.html"

        art = default_artifact_service.save_artifact(
            file_name=html_fname,
            content=html_str,
            user_id=user_id,
            session_id=session_id,
            mime_type="text/html"
        )

        return {
            "success": True,
            "chart_type": chart_type,
            "title": clean_title,
            "artifact_id": art.artifact_id,
            "file_path": art.file_path,
            "html_snippet": html_str[:1000] + "... (truncated)",
            "download_url": art.preview_url
        }

    except Exception as e:
        logger.warning(f"Plotly generation failed, falling back to Matplotlib: {e}")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 5))
        if len(cols) >= 2:
            plt.plot(df[cols[0]], df[cols[1]], marker='o')
        elif len(cols) == 1:
            plt.plot(df[cols[0]], marker='o')

        plt.title(clean_title)
        if x_label:
            plt.xlabel(x_label)
        if y_label:
            plt.ylabel(y_label)
        plt.tight_layout()

        png_fname = f"chart_{chart_type}_{uuid.uuid4().hex[:6]}.png"
        out_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, png_fname)
        plt.savefig(out_path, dpi=150)
        plt.close()

        with open(out_path, "rb") as f:
            art = default_artifact_service.save_artifact(
                file_name=png_fname,
                content=f.read(),
                user_id=user_id,
                session_id=session_id,
                mime_type="image/png"
            )

        return {
            "success": True,
            "chart_type": chart_type,
            "title": clean_title,
            "artifact_id": art.artifact_id,
            "file_path": out_path,
            "download_url": art.preview_url
        }
