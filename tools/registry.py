"""
Central tool registry, tool definitions schema, and dispatcher.
Includes core tools and extended data, research, code, career, productivity, and media tools.
"""

from typing import Dict, Any

from tools.web_search import search_web, fetch_webpage_content
from tools.code_executor import execute_python_code
from tools.math_solver import solve_math_expression, calculate_finance
from tools.file_analyzer import analyze_file
from tools.doc_generator import generate_document
from tools.extended_tools import (
    query_table,
    auto_eda_report,
    train_baseline_model,
    run_statistical_test,
    make_interactive_chart,
    search_papers,
    search_documents,
    summarize_youtube,
    create_diagram,
    lint_and_format_code,
    run_unit_tests,
    read_github_repo,
    convert_currency,
    get_market_data,
    convert_units,
    translate_text,
    score_resume_match,
    create_calendar_file,
    read_image_text,
    transcribe_audio,
    speak_text
)
from tools.high_value_tools import (
    solve_math_step_by_step,
    explain_code_error,
    sql_playground,
    generate_quiz_flashcards,
    complexity_analyzer,
    leetcode_coach,
    resume_improver,
    git_assistant
)
from tools.rag import search_documents_semantic, compare_documents_semantic
from tools.study_engine import generate_exam_pattern_answers, generate_nptel_mcqs
from tools.coding_lab import run_coding_workspace
from tools.automl import train_and_compare_models, analyze_data_quality, compute_eda_dashboard_data
from core.vision import analyze_image_multimodal
from tools.weather import get_live_weather

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    # Core Tools
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live web for current facts, news, documentation, versions, or verification. Use only when fresh or external information is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to retrieve (default: 5)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage_content",
            "description": "Extract full readable text from a specific webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to inspect."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_weather",
            "description": "Retrieve real-time weather information and short-term forecasts for a city or location worldwide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location name (e.g. 'Tokyo', 'London', 'San Francisco')."
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Execute Python code for complex calculations, algorithmic problems, data processing, statistical operations, or plotting charts with matplotlib.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Valid Python code to execute."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "solve_math",
            "description": "Perform exact symbolic mathematics, solve algebraic equations, evaluate calculus, or compute limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression or equation (e.g. 'x**2 - 5*x + 6 = 0', 'diff(sin(x), x)')."
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["eval", "simplify", "solve_equation", "derivative", "integral"],
                        "description": "Type of math problem to solve."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_finance",
            "description": "Calculate compound interest, simple interest, or loan EMI with exact formulas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calc_type": {
                        "type": "string",
                        "enum": ["compound", "simple", "emi"],
                        "description": "Financial calculation type."
                    },
                    "principal": {
                        "type": "number",
                        "description": "Principal amount."
                    },
                    "rate_pct": {
                        "type": "number",
                        "description": "Annual interest rate percentage (e.g. 8.5)."
                    },
                    "time_years": {
                        "type": "number",
                        "description": "Time period in years."
                    },
                    "n_compounds": {
                        "type": "integer",
                        "description": "Compounds per year (1 for annual, 12 for monthly)."
                    }
                },
                "required": ["calc_type", "principal", "rate_pct", "time_years"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_file",
            "description": "Read, inspect, and analyze uploaded or local files (PDF, CSV, Excel, DOCX, TXT, JSON, code).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to inspect."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_document",
            "description": "Generate an exportable file (PDF, DOCX, XLSX, CSV, Markdown, TXT) and save it to the outputs directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format_type": {
                        "type": "string",
                        "enum": ["pdf", "docx", "xlsx", "csv", "md", "txt"],
                        "description": "Target file format."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the document."
                    },
                    "content": {
                        "type": "string",
                        "description": "Main body text or content."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional specific filename."
                    }
                },
                "required": ["format_type", "title", "content"]
            }
        }
    },
    # Extended Data and Analysis Tools
    {
        "type": "function",
        "function": {
            "name": "query_table",
            "description": "Execute SQL or question analysis on an uploaded CSV or Excel table (counts, totals, averages, groupings, filters).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to CSV or Excel file."},
                    "question": {"type": "string", "description": "Analytical question or SQL query."}
                },
                "required": ["file", "question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "auto_eda_report",
            "description": "Generate automated Exploratory Data Analysis (EDA) on a dataset: shape, types, missing values, duplicates, outliers, and summary statistics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to dataset file."}
                },
                "required": ["file"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "train_baseline_model",
            "description": "Train and evaluate a quick baseline machine learning model (classification or regression) with metrics and top feature importances.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to dataset."},
                    "target": {"type": "string", "description": "Name of the target column to predict."}
                },
                "required": ["file", "target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_statistical_test",
            "description": "Conduct hypothesis testing (t-test, ANOVA, chi-square, correlation) and return statistics and effect sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data description or file path."},
                    "question": {"type": "string", "description": "Statistical question and hypothesis to test."}
                },
                "required": ["data", "question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "make_interactive_chart",
            "description": "Prepare visualization specification or code for interactive charts (line, bar, scatter, histogram, box plot).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to data file."},
                    "request": {"type": "string", "description": "Chart request and columns to plot."}
                },
                "required": ["file", "request"]
            }
        }
    },
    # Extended Research Tools
    {
        "type": "function",
        "function": {
            "name": "search_papers",
            "description": "Search academic literature and research papers (arXiv, Semantic Scholar) with authors, year, and URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Academic topic or question."}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search across uploaded documents and local knowledge base for relevant passages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_youtube",
            "description": "Summarize a YouTube video, extracting key concepts, timestamps, and quiz questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube video link."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_diagram",
            "description": "Generate valid Mermaid diagram code for flowcharts, sequence diagrams, architecture diagrams, or ER diagrams.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Description of the workflow, system, or entities."}
                },
                "required": ["description"]
            }
        }
    },
    # Extended Code Tools
    {
        "type": "function",
        "function": {
            "name": "lint_and_format_code",
            "description": "Check code for syntax errors, style issues, bugs, and format cleanly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Source code to check."}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_unit_tests",
            "description": "Execute Python unit test assertions in the sandbox environment to verify code correctness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Implementation code."},
                    "tests": {"type": "string", "description": "Test cases or assert statements."}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_github_repo",
            "description": "Inspect and summarize a public GitHub repository, its structure, and README.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "GitHub repository URL."}
                },
                "required": ["url"]
            }
        }
    },
    # Everyday and Career Tools
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert money between currencies with benchmark rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to convert."},
                    "from_curr": {"type": "string", "description": "Source currency code (e.g. USD, EUR, INR)."},
                    "to_curr": {"type": "string", "description": "Target currency code."}
                },
                "required": ["amount", "from_curr", "to_curr"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_data",
            "description": "Retrieve current price quotes and trends for stocks, indices, or crypto tickers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Symbol or ticker (e.g. AAPL, BTC, NVDA)."}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_units",
            "description": "Convert physical units (length, weight, temperature, speed, volume) with exact conversion factors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Numeric value."},
                    "from_unit": {"type": "string", "description": "Source unit (e.g. km, miles, kg, lbs, C, F)."},
                    "to_unit": {"type": "string", "description": "Target unit."}
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "Translate text faithfully to a target language preserving technical formatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate."},
                    "language": {"type": "string", "description": "Target language."}
                },
                "required": ["text", "language"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "score_resume_match",
            "description": "Compare a resume against a job description, computing a match score, matching skills, and missing qualifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resume": {"type": "string", "description": "Resume text or summary."},
                    "jd": {"type": "string", "description": "Job description text."}
                },
                "required": ["resume", "jd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_file",
            "description": "Generate a downloadable .ics calendar file for a study schedule, plan, or deadlines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {"type": "string", "description": "Schedule or event details."},
                    "title": {"type": "string", "description": "Title of calendar event."}
                },
                "required": ["plan"]
            }
        }
    },
    # Media and Voice Tools
    {
        "type": "function",
        "function": {
            "name": "read_image_text",
            "description": "Extract and transcribe text or equations from an image or screenshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image": {"type": "string", "description": "Image file path."}
                },
                "required": ["image"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": "Transcribe recorded or uploaded speech audio files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audio": {"type": "string", "description": "Audio file path."}
                },
                "required": ["audio"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speak_text",
            "description": "Clean and format technical text into natural prose for text-to-speech output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to format for speech."}
                },
                "required": ["text"]
            }
        }
    }
]

CUSTOM_TOOL_REGISTRY: Dict[str, Any] = {}

def register_custom_tool(name: str, handler: Any, definition: Any = None):
    """
    Registers a custom extension tool dynamically.
    Allows zero-code-change extensions for third-party or mock tools.
    """
    clean_name = name.lower().strip()
    CUSTOM_TOOL_REGISTRY[clean_name] = handler
    if definition and isinstance(definition, dict):
        TOOL_DEFINITIONS.append(definition)


def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a requested tool by name with arguments and returns structured output.
    Validates arguments via Pydantic schemas before invocation.
    """
    # 0. Check dynamically registered custom tools first
    clean_name = tool_name.lower().strip()
    if clean_name in CUSTOM_TOOL_REGISTRY:
        try:
            handler = CUSTOM_TOOL_REGISTRY[clean_name]
            res = handler(**arguments) if callable(handler) else handler
            return {"tool": tool_name, "success": True, "result": res}
        except Exception as e:
            return {"tool": tool_name, "success": False, "error": str(e)}

    from tools.schemas import validate_tool_arguments
    is_valid, validated_args, val_error = validate_tool_arguments(tool_name, arguments)
    if not is_valid:
        return {"tool": tool_name, "error": val_error}
    if validated_args is not None:
        arguments = validated_args

    try:
        # Core Tools
        if tool_name == "search_web":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            results = search_web(query, max_results=max_results)
            return {"tool": tool_name, "result": results}

        elif tool_name == "fetch_webpage_content":
            url = arguments.get("url", "")
            content = fetch_webpage_content(url)
            return {"tool": tool_name, "content": content}

        elif tool_name == "execute_python_code":
            code = arguments.get("code", "")
            res = execute_python_code(code)
            return {"tool": tool_name, "result": res}

        elif tool_name == "solve_math":
            expr = arguments.get("expression", "")
            task_type = arguments.get("task_type", "eval")
            res = solve_math_expression(expr, task_type)
            return {"tool": tool_name, "result": res}

        elif tool_name == "calculate_finance":
            calc_type = arguments.get("calc_type", "compound")
            p = float(arguments.get("principal", 0))
            r = float(arguments.get("rate_pct", 0))
            t = float(arguments.get("time_years", 0))
            n = int(arguments.get("n_compounds", 1))
            res = calculate_finance(calc_type, p, r, t, n)
            return {"tool": tool_name, "result": res}

        elif tool_name == "analyze_file":
            path = arguments.get("file_path", "")
            res = analyze_file(path)
            return {"tool": tool_name, "result": res}

        elif tool_name == "generate_document":
            fmt = arguments.get("format_type", "md")
            title = arguments.get("title", "Document")
            content = arguments.get("content", "")
            filename = arguments.get("filename")
            res = generate_document(fmt, title, content, filename=filename)
            return {"tool": tool_name, "result": res}

        # Data & Analysis Tools
        elif tool_name == "query_table":
            file_p = arguments.get("file", "")
            q = arguments.get("question", "")
            return {"tool": tool_name, "result": query_table(file_p, q)}

        elif tool_name == "auto_eda_report":
            file_p = arguments.get("file", "")
            return {"tool": tool_name, "result": auto_eda_report(file_p)}

        elif tool_name == "train_baseline_model":
            file_p = arguments.get("file", "")
            target = arguments.get("target", "")
            return {"tool": tool_name, "result": train_baseline_model(file_p, target)}

        elif tool_name == "run_statistical_test":
            data = arguments.get("data", "")
            q = arguments.get("question", "")
            return {"tool": tool_name, "result": run_statistical_test(data, q)}

        elif tool_name == "make_interactive_chart":
            file_p = arguments.get("file", "")
            req = arguments.get("request", "")
            return {"tool": tool_name, "result": make_interactive_chart(file_p, req)}

        # Research Tools
        elif tool_name == "search_papers":
            topic = arguments.get("topic", "")
            return {"tool": tool_name, "result": search_papers(topic)}

        elif tool_name == "search_documents":
            q = arguments.get("query", "")
            return {"tool": tool_name, "result": search_documents(q)}

        elif tool_name == "summarize_youtube":
            url = arguments.get("url", "")
            return {"tool": tool_name, "result": summarize_youtube(url)}

        elif tool_name == "create_diagram":
            desc = arguments.get("description", "")
            return {"tool": tool_name, "result": create_diagram(desc)}

        # Code Tools
        elif tool_name == "lint_and_format_code":
            code = arguments.get("code", "")
            return {"tool": tool_name, "result": lint_and_format_code(code)}

        elif tool_name == "run_unit_tests":
            code = arguments.get("code", "")
            tests = arguments.get("tests", "")
            return {"tool": tool_name, "result": run_unit_tests(code, tests)}

        elif tool_name == "read_github_repo":
            url = arguments.get("url", "")
            return {"tool": tool_name, "result": read_github_repo(url)}

        # Everyday & Career Tools
        elif tool_name == "convert_currency":
            amt = float(arguments.get("amount", 0))
            fc = arguments.get("from_curr") or arguments.get("from") or "USD"
            tc = arguments.get("to_curr") or arguments.get("to") or "EUR"
            return {"tool": tool_name, "result": convert_currency(amt, fc, tc)}

        elif tool_name == "get_market_data":
            ticker = arguments.get("ticker", "")
            return {"tool": tool_name, "result": get_market_data(ticker)}

        elif tool_name == "convert_units":
            val = float(arguments.get("value", 0))
            fu = arguments.get("from_unit") or arguments.get("from") or "m"
            tu = arguments.get("to_unit") or arguments.get("to") or "ft"
            return {"tool": tool_name, "result": convert_units(val, fu, tu)}

        elif tool_name == "translate_text":
            txt = arguments.get("text", "")
            lang = arguments.get("language", "English")
            return {"tool": tool_name, "result": translate_text(txt, lang)}

        elif tool_name == "score_resume_match":
            res = arguments.get("resume", "")
            jd = arguments.get("jd", "")
            return {"tool": tool_name, "result": score_resume_match(res, jd)}

        elif tool_name == "create_calendar_file":
            plan = arguments.get("plan", "")
            title = arguments.get("title", "Schedule")
            return {"tool": tool_name, "result": create_calendar_file(plan, title)}

        # Vision & Audio Tools
        elif tool_name == "read_image_text":
            img = arguments.get("image", "")
            return {"tool": tool_name, "result": read_image_text(img)}

        elif tool_name == "transcribe_audio":
            aud = arguments.get("audio", "")
            return {"tool": tool_name, "result": transcribe_audio(aud)}

        elif tool_name == "speak_text":
            txt = arguments.get("text", "")
            return {"tool": tool_name, "result": speak_text(txt)}

        # High-Value Specialized Tools
        elif tool_name in ("solve_math_step_by_step", "math_step_by_step"):
            expr = arguments.get("expression") or arguments.get("expr", "")
            ttype = arguments.get("task_type", "solve")
            return {"tool": tool_name, "result": solve_math_step_by_step(expr, ttype)}

        elif tool_name == "explain_code_error":
            code = arguments.get("code", "")
            tb = arguments.get("traceback") or arguments.get("error", "")
            return {"tool": tool_name, "result": explain_code_error(code, tb)}

        elif tool_name == "sql_playground":
            q = arguments.get("query", "")
            csv_p = arguments.get("csv_path")
            return {"tool": tool_name, "result": sql_playground(q, csv_path=csv_p)}

        elif tool_name == "generate_quiz_flashcards":
            t = arguments.get("text") or arguments.get("topic", "")
            n = int(arguments.get("num_questions", 5))
            return {"tool": tool_name, "result": generate_quiz_flashcards(t, n)}

        elif tool_name == "complexity_analyzer":
            c = arguments.get("code", "")
            return {"tool": tool_name, "result": complexity_analyzer(c)}

        elif tool_name == "leetcode_coach":
            prob = arguments.get("problem_title") or arguments.get("problem", "")
            att = arguments.get("user_attempt", "")
            hl = int(arguments.get("hint_level", 1))
            return {"tool": tool_name, "result": leetcode_coach(prob, att, hl)}

        elif tool_name == "resume_improver":
            b = arguments.get("bullet_point") or arguments.get("bullet", "")
            role = arguments.get("target_role", "Software Engineer")
            return {"tool": tool_name, "result": resume_improver(b, role)}

        elif tool_name == "git_assistant":
            diff = arguments.get("diff_text") or arguments.get("diff", "")
            task = arguments.get("task", "commit_message")
            return {"tool": tool_name, "result": git_assistant(diff, task)}

        elif tool_name == "search_documents_semantic":
            q = arguments.get("query", "")
            return {"tool": tool_name, "result": search_documents_semantic(q)}

        elif tool_name == "compare_documents_semantic":
            q = arguments.get("query", "")
            return {"tool": tool_name, "result": compare_documents_semantic(q)}

        elif tool_name == "generate_exam_pattern_answers":
            t = arguments.get("topic") or arguments.get("text", "")
            p = arguments.get("pattern", "all")
            return {"tool": tool_name, "result": generate_exam_pattern_answers(t, p)}

        elif tool_name == "generate_nptel_mcqs":
            t = arguments.get("topic") or arguments.get("text", "")
            n = int(arguments.get("num_questions", 5))
            diff = arguments.get("difficulty", "moderate")
            return {"tool": tool_name, "result": generate_nptel_mcqs(t, n, diff)}

        elif tool_name == "run_coding_workspace":
            c = arguments.get("code", "")
            inp = arguments.get("stdin_input", "")
            tcs = arguments.get("test_cases", [])
            return {"tool": tool_name, "result": run_coding_workspace(c, stdin_input=inp, test_cases=tcs)}

        elif tool_name == "train_and_compare_models":
            f_path = arguments.get("file_path", "")
            target = arguments.get("target_column", "")
            return {"tool": tool_name, "result": train_and_compare_models(f_path, target)}

        elif tool_name == "analyze_image_multimodal":
            img_p = arguments.get("image_path", "")
            p = arguments.get("prompt", "Analyze this image.")
            mode = arguments.get("task_mode", "general")
            return {"tool": tool_name, "result": analyze_image_multimodal(img_p, p, mode)}

        elif tool_name == "get_live_weather":
            loc = arguments.get("location") or arguments.get("city", "")
            return {"tool": tool_name, "result": get_live_weather(loc)}

        else:
            # Check Central Tool Registry for extended blueprint capabilities
            from core.tool_registry import default_tool_registry
            from core.tool_contracts import ToolInvocation
            if default_tool_registry.get_tool(tool_name):
                invocation = ToolInvocation(tool_name=tool_name, arguments=arguments)
                tool_res = default_tool_registry.execute(invocation)
                return {
                    "tool": tool_name,
                    "result": tool_res.data,
                    "success": tool_res.success,
                    "error": tool_res.error,
                    "duration_ms": tool_res.duration_ms,
                    "artifacts": tool_res.artifacts
                }
            return {"tool": tool_name, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"tool": tool_name, "error": str(e)}
