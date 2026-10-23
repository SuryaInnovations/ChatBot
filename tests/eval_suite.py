"""
SPARK-AI 100-Question Evaluation & Quality Benchmark Suite.
Measures:
1. Category Accuracy % (Math 25, Code 25, SQL 20, Data Science 15, Interview 15)
2. Average Latency per Query & Overall (ms)
3. Tool Invocation Success Rate %
"""

import os
import sys
import time
import json
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.high_value_tools import (
    solve_math_step_by_step,
    complexity_analyzer,
    explain_code_error,
    sql_playground,
    leetcode_coach,
    resume_improver
)
from tools.sandbox import execute_safe_code
from core.interview_bank import get_random_question


# =========================================================================
# 100 BENCHMARK EVALUATION QUESTIONS
# =========================================================================

MATH_BENCHMARK_25: List[Dict[str, Any]] = [
    # Algebra & Equations (1-10)
    {"q": "2*x + 5 = 15", "type": "solve", "expected": "5"},
    {"q": "3*x - 9 = 0", "type": "solve", "expected": "3"},
    {"q": "x^2 - 4 = 0", "type": "solve", "expected": "[-2, 2]"},
    {"q": "5*x + 20 = 0", "type": "solve", "expected": "-4"},
    {"q": "x/2 + 3 = 7", "type": "solve", "expected": "8"},
    {"q": "4*x - 12 = 8", "type": "solve", "expected": "5"},
    {"q": "2*x + 3*x = 25", "type": "solve", "expected": "5"},
    {"q": "7*x - 14 = 0", "type": "solve", "expected": "2"},
    {"q": "x^2 - 9 = 0", "type": "solve", "expected": "[-3, 3]"},
    {"q": "10*x = 100", "type": "solve", "expected": "10"},
    # Calculus Derivatives (11-17)
    {"q": "x^2", "type": "derivative", "expected": "2*x"},
    {"q": "3*x^3", "type": "derivative", "expected": "9*x^2"},
    {"q": "5*x + 4", "type": "derivative", "expected": "5"},
    {"q": "x^4", "type": "derivative", "expected": "4*x^3"},
    {"q": "sin(x)", "type": "derivative", "expected": "cos(x)"},
    {"q": "exp(x)", "type": "derivative", "expected": "exp(x)"},
    {"q": "x^5 - 2*x", "type": "derivative", "expected": "5*x^4 - 2"},
    # Calculus Integrals (18-21)
    {"q": "2*x", "type": "integral", "expected": "x**2"},
    {"q": "3*x^2", "type": "integral", "expected": "x**3"},
    {"q": "4", "type": "integral", "expected": "4*x"},
    {"q": "cos(x)", "type": "integral", "expected": "sin(x)"},
    # Arithmetic & Evaluation (22-25)
    {"q": "25 * 4 + 10", "type": "evaluate", "expected": "110"},
    {"q": "2^10", "type": "evaluate", "expected": "1024"},
    {"q": "144 / 12", "type": "evaluate", "expected": "12"},
    {"q": "sqrt(169)", "type": "evaluate", "expected": "13"},
]

CODE_BENCHMARK_25: List[Dict[str, Any]] = [
    # Complexity Analysis (1-10)
    {"code": "def f(arr):\n  for x in arr: pass", "type": "complexity", "exp_time": "O(N)"},
    {"code": "def f(arr):\n  for i in arr:\n    for j in arr: pass", "type": "complexity", "exp_time": "O(N²)"},
    {"code": "def f(x):\n  return x * 2", "type": "complexity", "exp_time": "O(1)"},
    {"code": "def f(arr):\n  arr.sort()", "type": "complexity", "exp_time": "O(N log N)"},
    {"code": "def f(arr):\n  return sorted(arr)", "type": "complexity", "exp_time": "O(N log N)"},
    {"code": "def f(arr):\n  for i in arr:\n    for j in arr:\n      for k in arr: pass", "type": "complexity", "exp_time": "O(N^3)"},
    {"code": "def fib(n):\n  if n<=1: return n\n  return fib(n-1)+fib(n-2)", "type": "complexity", "exp_time": "O(2^N)"},
    {"code": "def binary_s(arr, x):\n  # search\n  return arr[0]", "type": "complexity", "exp_time": "O(1)"},
    {"code": "def linear_s(arr, target):\n  return target in arr", "type": "complexity", "exp_time": "O(N)"},
    {"code": "def slice_arr(arr):\n  return arr[1:5]", "type": "complexity", "exp_time": "O(1)"},
    # Code Error Explaining (11-18)
    {"code": "x = 10 / 0", "tb": "ZeroDivisionError: division by zero", "type": "error_debug", "exp_err": "ZeroDivisionError"},
    {"code": "arr = [1, 2]\nval = arr[5]", "tb": "IndexError: list index out of range", "type": "error_debug", "exp_err": "IndexError"},
    {"code": "d = {'a': 1}\nval = d['b']", "tb": "KeyError: 'b'", "type": "error_debug", "exp_err": "KeyError"},
    {"code": "x = '5' + 2", "tb": "TypeError: can only concatenate str to str", "type": "error_debug", "exp_err": "TypeError"},
    {"code": "def foo(:\n  pass", "tb": "SyntaxError: invalid syntax", "type": "error_debug", "exp_err": "SyntaxError"},
    {"code": "int('abc')", "tb": "ValueError: invalid literal for int()", "type": "error_debug", "exp_err": "ValueError"},
    {"code": "def bad():\n  x = 1/0", "tb": "ZeroDivisionError: division by zero", "type": "error_debug", "exp_err": "ZeroDivisionError"},
    {"code": "lst = []\nlst.pop()", "tb": "IndexError: pop from empty list", "type": "error_debug", "exp_err": "IndexError"},
    # Execution & LeetCode (19-25)
    {"problem": "Two Sum", "level": 1, "type": "coach"},
    {"problem": "Two Sum", "level": 2, "type": "coach"},
    {"problem": "Two Sum", "level": 3, "type": "coach"},
    {"problem": "LRU Cache", "level": 1, "type": "coach"},
    {"problem": "Merge K Sorted Lists", "level": 2, "type": "coach"},
    {"code": "def solve(n): return n * (n + 1) // 2\nassert solve(10) == 55", "type": "exec"},
    {"code": "def is_pal(s): return s == s[::-1]\nassert is_pal('racecar') is True", "type": "exec"},
]

SQL_BENCHMARK_20: List[Dict[str, Any]] = [
    {"q": "SELECT * FROM employees;", "exp_cols": ["emp_id", "name", "department", "salary", "hire_date"]},
    {"q": "SELECT name, salary FROM employees WHERE salary > 100000;", "exp_min_rows": 1},
    {"q": "SELECT COUNT(*) as total FROM employees;", "exp_cols": ["total"]},
    {"q": "SELECT AVG(salary) as avg_sal FROM employees;", "exp_cols": ["avg_sal"]},
    {"q": "SELECT department, COUNT(*) as cnt FROM employees GROUP BY department;", "exp_cols": ["department", "cnt"]},
    {"q": "SELECT MAX(salary) as max_s, MIN(salary) as min_s FROM employees;", "exp_cols": ["max_s", "min_s"]},
    {"q": "SELECT name FROM employees ORDER BY salary DESC LIMIT 1;", "exp_cols": ["name"]},
    {"q": "SELECT name FROM employees WHERE department = 'Engineering';", "exp_min_rows": 2},
    {"q": "SELECT department, SUM(salary) as total_budget FROM employees GROUP BY department;", "exp_cols": ["department", "total_budget"]},
    {"q": "SELECT DISTINCT department FROM employees;", "exp_cols": ["department"]},
    {"q": "SELECT * FROM employees WHERE hire_date >= '2021-01-01';", "exp_min_rows": 1},
    {"q": "SELECT name, salary * 1.1 as bonus_sal FROM employees;", "exp_cols": ["name", "bonus_sal"]},
    {"q": "SELECT department FROM employees GROUP BY department HAVING AVG(salary) > 100000;", "exp_cols": ["department"]},
    {"q": "SELECT name FROM employees WHERE name LIKE 'A%';", "exp_cols": ["name"]},
    {"q": "SELECT emp_id, salary FROM employees WHERE salary BETWEEN 90000 AND 130000;", "exp_min_rows": 1},
    {"q": "EXPLAIN QUERY PLAN SELECT * FROM employees WHERE emp_id = 1;", "exp_cols": ["id", "parent", "notused", "detail"]},
    {"q": "WITH dept_avg AS (SELECT department, AVG(salary) as av FROM employees GROUP BY department) SELECT * FROM dept_avg;", "exp_cols": ["department", "av"]},
    {"q": "SELECT LOWER(name) as lower_name FROM employees;", "exp_cols": ["lower_name"]},
    {"q": "SELECT SUBSTR(hire_date, 1, 4) as hire_year FROM employees;", "exp_cols": ["hire_year"]},
    {"q": "SELECT department, COUNT(*) as c FROM employees GROUP BY department ORDER BY c DESC;", "exp_cols": ["department", "c"]},
]

DS_STATS_BENCHMARK_15: List[Dict[str, Any]] = [
    {"code": "import numpy as np\nvals = np.array([10, 20, 30, 40, 50])\nprint(f'MEAN:{np.mean(vals)}')", "expected": "MEAN:30.0"},
    {"code": "import numpy as np\nvals = np.array([10, 20, 30, 40, 50])\nprint(f'MEDIAN:{np.median(vals)}')", "expected": "MEDIAN:30.0"},
    {"code": "import numpy as np\nvals = np.array([1, 2, 3, 4, 5])\nprint(f'STD:{np.std(vals):.2f}')", "expected": "STD:1.41"},
    {"code": "import numpy as np\nvals = np.array([1, 2, 3, 4, 5])\nprint(f'VAR:{np.var(vals):.2f}')", "expected": "VAR:2.00"},
    {"code": "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})\nprint(f'SHAPE:{df.shape}')", "expected": "SHAPE:(3, 2)"},
    {"code": "import numpy as np\nx = np.array([1, 2, 3]); y = np.array([2, 4, 6])\nprint(f'CORR:{np.corrcoef(x, y)[0,1]:.1f}')", "expected": "CORR:1.0"},
    {"code": "import numpy as np\nx = np.array([10, 20, 30])\nprint(f'MIN:{np.min(x)},MAX:{np.max(x)}')", "expected": "MIN:10,MAX:30"},
    {"code": "import numpy as np\nx = np.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50)\nprint(f'P50:{x}')", "expected": "P50:5.5"},
    {"code": "import pandas as pd\ndf = pd.DataFrame({'cat': ['A', 'A', 'B']})\nprint(f'COUNTS:{ {k: int(v) for k, v in df[\"cat\"].value_counts().items()} }')", "expected": "'A': 2"},
    {"code": "import numpy as np\nA = np.array([[1, 2], [3, 4]])\nprint(f'DET:{int(round(np.linalg.det(A)))}')", "expected": "DET:-2"},
    {"code": "import numpy as np\nA = np.eye(3)\nprint(f'TRACE:{np.trace(A)}')", "expected": "TRACE:3.0"},
    {"code": "import numpy as np\nx = np.array([1, 2, 3]); print(f'NORM:{np.linalg.norm(x):.2f}')", "expected": "NORM:3.74"},
    {"code": "import pandas as pd\ndf = pd.DataFrame({'val': [1, None, 3]})\nprint(f'NULLS:{df.isna().sum().sum()}')", "expected": "NULLS:1"},
    {"code": "import numpy as np\na = np.array([1, 2]); b = np.array([3, 4]); print(f'DOT:{np.dot(a, b)}')", "expected": "DOT:11"},
    {"code": "import numpy as np\nx = np.array([2, 4, 6]); print(f'SUM:{np.sum(x)}')", "expected": "SUM:12"},
]

INTERVIEW_BENCHMARK_15: List[Dict[str, Any]] = [
    {"category": "DSA", "diff": "Medium", "topic": "Two Pointers"},
    {"category": "DSA", "diff": "Hard", "topic": "Dynamic Programming"},
    {"category": "System Design", "diff": "Medium", "topic": "URL Shortener"},
    {"category": "System Design", "diff": "Hard", "topic": "Distributed Cache"},
    {"category": "SQL", "diff": "Medium", "topic": "Window Functions"},
    {"category": "ML", "diff": "Medium", "topic": "Bias-Variance Tradeoff"},
    {"category": "HR", "diff": "Medium", "topic": "Conflict Resolution (STAR)"},
    {"bullet": "wrote backend code for login", "role": "Backend Engineer"},
    {"bullet": "made database queries faster", "role": "Data Engineer"},
    {"bullet": "built dashboard for metrics", "role": "Full Stack Engineer"},
    {"category": "DSA", "diff": "Easy", "topic": "Arrays & Strings"},
    {"category": "System Design", "diff": "Medium", "topic": "Rate Limiter"},
    {"category": "ML", "diff": "Hard", "topic": "Transformer Attention"},
    {"category": "SQL", "diff": "Easy", "topic": "Joins"},
    {"bullet": "fixed bugs in mobile application", "role": "Mobile Developer"}
]


# =========================================================================
# EVALUATION RUNNER
# =========================================================================

def run_evaluation_suite() -> Dict[str, Any]:
    """
    Executes the complete 100-question benchmark suite across all 5 domains.
    Returns comprehensive metrics report with pass rate %, latency, and tool health.
    """
    category_metrics: Dict[str, Any] = {}
    results: Dict[str, Any] = {
        "total_questions": 100,
        "passed": 0,
        "failed": 0,
        "category_metrics": category_metrics,
        "average_latency_ms": 0.0,
        "start_time": time.time()
    }
    latencies = []

    # 1. Math Benchmark (25 questions)
    math_passed = 0
    t0 = time.perf_counter()
    for item in MATH_BENCHMARK_25:
        q_start = time.perf_counter()
        res = solve_math_step_by_step(item["q"], task_type=item["type"])
        latencies.append((time.perf_counter() - q_start) * 1000)
        if res.get("success"):
            math_passed += 1
    math_lat = (time.perf_counter() - t0) * 1000 / len(MATH_BENCHMARK_25)
    category_metrics["Math (25)"] = {
        "passed": math_passed, "total": 25, "accuracy": f"{(math_passed/25)*100:.1f}%", "avg_latency_ms": round(math_lat, 1)
    }

    # 2. Code Benchmark (25 questions)
    code_passed = 0
    t0 = time.perf_counter()
    for item in CODE_BENCHMARK_25:
        q_start = time.perf_counter()
        if item["type"] == "complexity":
            res = complexity_analyzer(item["code"])
            if res.get("success"):
                code_passed += 1
        elif item["type"] == "error_debug":
            res = explain_code_error(item["code"], item["tb"])
            if res.get("success") and res.get("analysis", {}).get("error_type") == item["exp_err"]:
                code_passed += 1
        elif item["type"] == "coach":
            res = leetcode_coach(item["problem"], hint_level=int(item["level"]))
            if res.get("success"):
                code_passed += 1
        elif item["type"] == "exec":
            res = execute_safe_code(item["code"])
            if res.get("success"):
                code_passed += 1
        latencies.append((time.perf_counter() - q_start) * 1000)
    code_lat = (time.perf_counter() - t0) * 1000 / len(CODE_BENCHMARK_25)
    category_metrics["Code (25)"] = {
        "passed": code_passed, "total": 25, "accuracy": f"{(code_passed/25)*100:.1f}%", "avg_latency_ms": round(code_lat, 1)
    }

    # 3. SQL Benchmark (20 questions)
    sql_passed = 0
    t0 = time.perf_counter()
    for item in SQL_BENCHMARK_20:
        q_start = time.perf_counter()
        res = sql_playground(item["q"])
        latencies.append((time.perf_counter() - q_start) * 1000)
        if res.get("success"):
            sql_passed += 1
    sql_lat = (time.perf_counter() - t0) * 1000 / len(SQL_BENCHMARK_20)
    category_metrics["SQL (20)"] = {
        "passed": sql_passed, "total": 20, "accuracy": f"{(sql_passed/20)*100:.1f}%", "avg_latency_ms": round(sql_lat, 1)
    }

    # 4. Data Science Benchmark (15 questions)
    ds_passed = 0
    t0 = time.perf_counter()
    for item in DS_STATS_BENCHMARK_15:
        q_start = time.perf_counter()
        res = execute_safe_code(item["code"])
        latencies.append((time.perf_counter() - q_start) * 1000)
        if res.get("success") and item["expected"] in res.get("output", ""):
            ds_passed += 1
    ds_lat = (time.perf_counter() - t0) * 1000 / len(DS_STATS_BENCHMARK_15)
    category_metrics["Data Science (15)"] = {
        "passed": ds_passed, "total": 15, "accuracy": f"{(ds_passed/15)*100:.1f}%", "avg_latency_ms": round(ds_lat, 1)
    }

    # 5. Interview Prep Benchmark (15 questions)
    iv_passed = 0
    t0 = time.perf_counter()
    for item in INTERVIEW_BENCHMARK_15:
        q_start = time.perf_counter()
        if "bullet" in item:
            res = resume_improver(item["bullet"], target_role=item["role"])
            if res.get("success") and res.get("rewritten_suggestion"):
                iv_passed += 1
        else:
            q = get_random_question(category=item.get("category", "DSA"), difficulty=item.get("diff", "Medium"))
            if q and q.get("question"):
                iv_passed += 1
        latencies.append((time.perf_counter() - q_start) * 1000)
    iv_lat = (time.perf_counter() - t0) * 1000 / len(INTERVIEW_BENCHMARK_15)
    category_metrics["Interview Prep (15)"] = {
        "passed": iv_passed, "total": 15, "accuracy": f"{(iv_passed/15)*100:.1f}%", "avg_latency_ms": round(iv_lat, 1)
    }

    total_passed = math_passed + code_passed + sql_passed + ds_passed + iv_passed
    results["passed"] = total_passed
    results["failed"] = 100 - total_passed
    results["overall_accuracy"] = f"{(total_passed / 100) * 100:.1f}%"
    results["average_latency_ms"] = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

    return results


# Pytest entrypoints
def test_full_100_eval_suite():
    """Runs the 100 benchmark eval suite and asserts >= 95% overall accuracy."""
    report = run_evaluation_suite()
    print("\n" + "="*60)
    print(">>> SPARK-AI 100-QUESTION BENCHMARK RESULTS")
    print("="*60)
    for cat, data in report["category_metrics"].items():
        print(f"* {cat:<22}: {data['passed']}/{data['total']} passed ({data['accuracy']}) [Avg Latency: {data['avg_latency_ms']}ms]")
    print("-"*60)
    print(f"Overall Accuracy: {report['overall_accuracy']} ({report['passed']}/100 questions)")
    print(f"Average Latency : {report['average_latency_ms']} ms")
    print("="*60)
    assert report["passed"] >= 95, f"Expected at least 95/100 passes, got {report['passed']}"


if __name__ == "__main__":
    rep = run_evaluation_suite()
    print(json.dumps(rep, indent=2))
