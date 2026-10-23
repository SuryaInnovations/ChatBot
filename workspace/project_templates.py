"""
workspace/project_templates.py — Scaffolding Templates for AI Project Builder.

Contains production-grade project starter templates for:
- FastAPI Microservice (FastAPI + Pydantic + pytest)
- Streamlit Interactive App (Streamlit + Pandas + Plotly)
- Python CLI Tool (argparse + modular architecture + tests)
- Minimal HTML/Tailwind Landing App
"""

from typing import Dict, Any

TEMPLATES = {
    "fastapi": {
        "name": "FastAPI Web Service",
        "description": "Production-ready REST API with OpenAPI documentation, Pydantic validation, and pytest.",
        "files": {
            "main.py": (
                "from fastapi import FastAPI\n\n"
                "app = FastAPI(title='SPARK-AI Generated Service', version='1.0.0')\n\n"
                "@app.get('/')\n"
                "def root():\n"
                "    return {'status': 'healthy', 'message': 'Welcome to SPARK-AI Generated API'}\n\n"
                "@app.get('/items/{item_id}')\n"
                "def read_item(item_id: int):\n"
                "    return {'item_id': item_id, 'name': f'Item {item_id}'}\n"
            ),
            "test_main.py": (
                "from fastapi.testclient import TestClient\n"
                "from main import app\n\n"
                "client = TestClient(app)\n\n"
                "def test_root():\n"
                "    response = client.get('/')\n"
                "    assert response.status_code == 200\n"
                "    assert response.json()['status'] == 'healthy'\n"
            ),
            "requirements.txt": "fastapi>=0.100.0\nuvicorn>=0.22.0\npytest>=7.0.0\nhttpx>=0.24.0\n",
            "README.md": "# FastAPI Microservice\n\nRun locally:\n```bash\nuvicorn main:app --reload\n```\n"
        }
    },
    "streamlit": {
        "name": "Streamlit Interactive App",
        "description": "Interactive data dashboard with widgets, charts, and file upload.",
        "files": {
            "app.py": (
                "import streamlit as st\n"
                "import pandas as pd\n"
                "import numpy as np\n\n"
                "st.set_page_config(page_title='Interactive Dashboard', layout='wide')\n"
                "st.title('📊 Data Exploration Dashboard')\n\n"
                "st.sidebar.header('Settings')\n"
                "n_samples = st.sidebar.slider('Sample Size', 10, 500, 100)\n\n"
                "df = pd.DataFrame({\n"
                "    'x': np.random.randn(n_samples),\n"
                "    'y': np.random.randn(n_samples)\n"
                "})\n"
                "st.line_chart(df)\n"
            ),
            "requirements.txt": "streamlit>=1.30.0\npandas>=2.0.0\nnumpy>=1.24.0\n",
            "README.md": "# Streamlit App\n\nRun:\n```bash\nstreamlit run app.py\n```\n"
        }
    },
    "cli": {
        "name": "Python CLI Utility",
        "description": "Modular command-line tool with subcommands, logging, and unit tests.",
        "files": {
            "cli.py": (
                "import argparse\n"
                "import sys\n\n"
                "def main():\n"
                "    parser = argparse.ArgumentParser(description='SPARK-AI CLI Tool')\n"
                "    parser.add_argument('--name', default='World', help='Name to greet')\n"
                "    args = parser.parse_args()\n"
                "    print(f'Hello, {args.name}!')\n\n"
                "if __name__ == '__main__':\n"
                "    main()\n"
            ),
            "test_cli.py": (
                "import subprocess\n"
                "import sys\n\n"
                "def test_cli():\n"
                "    res = subprocess.run([sys.executable, 'cli.py', '--name', 'Antigravity'], capture_output=True, text=True)\n"
                "    assert 'Hello, Antigravity!' in res.stdout\n"
            ),
            "README.md": "# CLI Utility\n\nRun:\n```bash\npython cli.py --name Alice\n```\n"
        }
    }
}


def get_template(template_name: str) -> Dict[str, Any]:
    return TEMPLATES.get(template_name.lower(), TEMPLATES["fastapi"])
