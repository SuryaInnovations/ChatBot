"""
Central tool registry, tool definitions schema, and dispatcher.
"""

import json
from typing import Dict, Any, List

from tools.web_search import search_web, fetch_webpage_content
from tools.code_executor import execute_python_code
from tools.math_solver import solve_math_expression, calculate_finance
from tools.file_analyzer import analyze_file
from tools.doc_generator import generate_document

TOOL_DEFINITIONS = [
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
    }
]

def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a requested tool by name with arguments and returns structured output.
    """
    try:
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

        else:
            return {"tool": tool_name, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"tool": tool_name, "error": str(e)}
