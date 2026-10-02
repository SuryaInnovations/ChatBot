"""
End-to-End Test Suite for All-in-One AI Assistant.
Verifies tools, pipeline orchestrator, and fallback behavior.
"""

import os
import sys
import unittest

# Ensure workspace in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.math_solver import solve_math_expression, calculate_finance
from tools.code_executor import execute_python_code
from tools.web_search import search_web
from tools.doc_generator import generate_document
from tools.file_analyzer import analyze_file
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.orchestrator import ChatbotOrchestrator

class TestAllInOneAssistant(unittest.TestCase):

    def test_01_math_solver(self):
        # Equation solving: x^2 - 5*x + 6 = 0
        res = solve_math_expression("x**2 - 5*x + 6 = 0", task_type="solve_equation")
        self.assertTrue(res.get("success"))
        self.assertIn("2", res.get("solutions", []))
        self.assertIn("3", res.get("solutions", []))

    def test_02_finance_calculation(self):
        # Compound interest: ₹25,000 at 8% for 3 years
        res = calculate_finance("compound", principal=25000, rate_pct=8, time_years=3)
        self.assertTrue(res.get("success"))
        # 25000 * (1.08)^3 = 31492.8
        self.assertAlmostEqual(res.get("total_amount"), 31492.80, places=1)

    def test_03_code_executor_and_plots(self):
        code = """
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 50)
y = np.sin(x)
plt.plot(x, y)
plt.title("Sine Wave")
print("Calculation complete:", len(x))
"""
        res = execute_python_code(code)
        self.assertTrue(res.get("success"))
        self.assertIn("Calculation complete: 50", res.get("stdout"))
        self.assertGreaterEqual(len(res.get("generated_images", [])), 1)

    def test_04_document_generation(self):
        res = generate_document(
            format_type="pdf",
            title="Automated Test Report",
            content="This is an automated test verifying the PDF generation pipeline.",
            filename="test_report.pdf"
        )
        self.assertTrue(res.get("success"))
        self.assertTrue(os.path.exists(res.get("file_path")))

    def test_05_file_analyzer(self):
        # Analyze the generated test PDF
        pdf_path = os.path.join(os.getcwd(), "outputs", "test_report.pdf")
        res = analyze_file(pdf_path)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("file_type"), "PDF")

    def test_06_web_search(self):
        res = search_web("Python programming language", max_results=2)
        self.assertIsInstance(res, list)
        self.assertGreaterEqual(len(res), 1)

    def test_07_orchestrator_pipeline(self):
        provider = LLMProvider(provider="autonomous_local")
        orchestrator = ChatbotOrchestrator(provider=provider)
        session = ConversationSession()

        # Test financial request routing
        result = orchestrator.process_message(
            session=session,
            user_message="How much will ₹25,000 become after 8% annual interest for 3 years?"
        )
        self.assertTrue(result.get("success"))
        self.assertIn("₹31,492.80", result.get("content"))
        self.assertEqual(len(session.messages), 2)

if __name__ == "__main__":
    unittest.main()
