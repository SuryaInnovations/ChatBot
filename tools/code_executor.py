"""
Safe Python code execution engine with stdout, stderr, and chart image capture.
"""

import sys
import io
import os
import uuid
import traceback
from typing import Dict, Any, List

def execute_python_code(code: str) -> Dict[str, Any]:
    """
    Executes Python code, capturing stdout, stderr, and any generated matplotlib figures.
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_stdout = io.StringIO()
    redirected_stderr = io.StringIO()
    sys.stdout = redirected_stdout
    sys.stderr = redirected_stderr

    # Ensure artifacts directory exists for charts
    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    generated_images: List[str] = []
    success = True
    error_message = None

    # Environment globals
    exec_globals: Dict[str, Any] = {
        "__builtins__": __builtins__,
    }

    try:
        # Pre-import common scientific packages if available
        import numpy as np
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        exec_globals["np"] = np
        exec_globals["pd"] = pd
        exec_globals["plt"] = plt
        exec_globals["matplotlib"] = matplotlib

        # Clear any prior plots
        plt.close("all")

        # Execute code
        exec(code, exec_globals)

        # Check if matplotlib has open figures
        if plt.get_fignums():
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                img_filename = f"chart_{uuid.uuid4().hex[:8]}.png"
                img_path = os.path.join(artifacts_dir, img_filename)
                fig.savefig(img_path, bbox_inches="tight", dpi=150)
                generated_images.append(img_path)
            plt.close("all")

    except Exception:
        success = False
        error_message = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    stdout_val = redirected_stdout.getvalue()
    stderr_val = redirected_stderr.getvalue()

    return {
        "success": success,
        "stdout": stdout_val.strip(),
        "stderr": stderr_val.strip() if not error_message else (stderr_val.strip() + "\n" + error_message).strip(),
        "generated_images": generated_images
    }
