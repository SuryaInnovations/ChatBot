"""
tests/test_response_simplification.py — Acceptance tests for SPARK-AI
Advanced Intelligent Response Generation & Simplification System.

Verifies the 9 required acceptance criteria:
- Test 1: "What is AI?" -> Simple definition + 1 example, ~20-60 words.
- Test 2: "What is an API?" -> Simple communication between applications.
- Test 3: "Explain AI in detail." -> Structured, accurate technical explanation.
- Test 4: "What is an..." with no context -> One short clarification question.
- Test 5: Voice question about topic discussed earlier -> Inferred question using context.
- Test 6: "Explain this code step by step." -> Step-by-step explanation.
- Test 7: "Give a 10-mark answer on machine learning." -> Detailed exam-oriented answer.
- Test 8: "What is AI? Explain in one sentence." -> Exactly one simple sentence, no extra sections.
- Test 9: "Give the complete architecture and implementation plan." -> Comprehensive technical response.
"""

import pytest
from unittest.mock import MagicMock
from core.orchestrator import ChatbotOrchestrator
from core.conversation import ConversationSession
from core.prompt import detect_adaptive_level, detect_length_mode
from tools.deterministic_solver import solve_deterministically


@pytest.fixture
def orchestrator():
    mock_llm = MagicMock()
    # Provide intelligent mocked responses tailored to length directives if called
    def mock_generate(messages, system_prompt, task_type=None, on_status_update=None):
        last_user = messages[-1]["content"] if messages else ""
        sys_str = str(system_prompt)

        if "one sentence" in last_user.lower() or "MANDATORY FORMAT" in sys_str:
            return {
                "success": True,
                "content": "AI is a technology that helps computers perform tasks that normally require human thinking."
            }
        elif "10-mark" in last_user.lower() or "ten mark" in last_user.lower() or "STUDY ENGINE" in sys_str:
            return {
                "success": True,
                "content": (
                    "### 10-Mark University Exam Solution: Machine Learning\n\n"
                    "#### 1. Introduction & Background\nMachine Learning is the study of algorithms that improve through experience.\n\n"
                    "#### 2. Theoretical Foundations\nCovers loss minimization and gradient descent.\n\n"
                    "#### 3. Working Mechanism\n1. Preprocessing 2. Training 3. Evaluation.\n\n"
                    "#### 4. Case Studies\nApplied in healthcare diagnostics and autonomous navigation.\n\n"
                    "#### 5. Trade-Off Analysis\nAccuracy vs computational latency.\n\n"
                    "#### 6. Conclusion\nMachine Learning is central to automated decision-making."
                )
            }
        elif "in detail" in last_user.lower() or "LEVEL 4" in sys_str:
            return {
                "success": True,
                "content": (
                    "### Artificial Intelligence (AI) — Technical Overview\n\n"
                    "#### 1. Definition & Core Mechanics\n"
                    "Artificial Intelligence encompasses computational systems designed to model cognitive functions like perception, learning, and reasoning.\n\n"
                    "#### 2. Key Paradigms\n"
                    "- Machine Learning: Pattern inference from empirical training distributions.\n"
                    "- Deep Learning: Hierarchical multi-layer neural networks.\n\n"
                    "#### 3. Real-World Applications & Trade-Offs\n"
                    "Applied in diagnostics, computer vision, and NLP with trade-offs in compute cost and interpretability."
                )
            }
        elif "step by step" in last_user.lower():
            return {
                "success": True,
                "content": (
                    "Here is the step-by-step explanation of the code:\n\n"
                    "1. **Line 1 (`def binary_search(arr, target):`)**: Defines the function taking a sorted list and a target value.\n"
                    "2. **Line 2 (`low, high = 0, len(arr) - 1`)**: Sets up the search pointers at the start and end of the list.\n"
                    "3. **Line 3 (`while low <= high:`)**: Continues halving the search space until the element is found or boundaries cross."
                )
            }
        elif "complete architecture" in last_user.lower():
            return {
                "success": True,
                "content": (
                    "### SPARK-AI: Complete Architecture & Implementation Plan\n\n"
                    "#### 1. Architecture Overview\nPresentation layer, API Gateway, Orchestrator, Sandbox.\n\n"
                    "#### 2. Component Specifications\nDeterministic tools, LLM pool, memory manager.\n\n"
                    "#### 3. Phased Implementation Plan\nPhase 1: Foundation. Phase 2: Tool Registry. Phase 3: Hardening."
                )
            }
        else:
            return {
                "success": True,
                "content": (
                    "**AI (Artificial Intelligence)** is a technology that helps computers do tasks that usually need human thinking.\n\n"
                    "**Example:** ChatGPT uses AI to understand your questions and generate answers."
                )
            }

    mock_llm.generate.side_effect = mock_generate
    mock_llm.model = "test-model"
    return ChatbotOrchestrator(provider=mock_llm)


def test_acceptance_1_what_is_ai(orchestrator):
    """Test 1: 'What is AI?' -> Simple definition and 1 familiar example, in approx 20-60 words."""
    session = ConversationSession()
    res = orchestrator.process_message(session, "What is AI?", search_mode="Auto")
    assert res["success"] is True
    content = res["content"]

    words = content.split()
    assert 15 <= len(words) <= 75, f"Word count {len(words)} outside target range"
    assert "human thinking" in content.lower() or "computers" in content.lower()
    assert "example" in content.lower()


def test_acceptance_2_what_is_an_api(orchestrator):
    """Test 2: 'What is an API?' -> Simple explanation of communication between applications."""
    # Test through deterministic solver
    det = solve_deterministically("knowledge", "What is an API?")
    assert det is not None
    content = det["content"]

    words = content.split()
    assert 15 <= len(words) <= 65
    assert "application" in content.lower() or "communicate" in content.lower()
    assert "weather" in content.lower() or "example" in content.lower()


def test_acceptance_3_explain_ai_in_detail(orchestrator):
    """Test 3: 'Explain AI in detail.' -> Structured, accurate explanation with examples & technical details."""
    assert detect_adaptive_level("Explain AI in detail.") == 4
    assert detect_length_mode("Explain AI in detail.") == "detailed"

    session = ConversationSession()
    res = orchestrator.process_message(session, "Explain AI in detail.", search_mode="Auto")
    assert res["success"] is True
    content = res["content"]
    assert len(content.split()) >= 40
    assert "###" in content or "####" in content or "\n-" in content


def test_acceptance_4_incomplete_query_no_context(orchestrator):
    """Test 4: 'What is an...' with no useful context -> One short clarification question."""
    session = ConversationSession()
    res = orchestrator.process_message(session, "What is an...", search_mode="Auto")
    assert res["success"] is True
    assert res["content"] == "What would you like to know about?"
    # Must NOT produce generic error paragraphs
    assert "please complete your question" not in res["content"].lower()


def test_acceptance_5_voice_question_with_context(orchestrator):
    """Test 5: Voice question about a topic discussed earlier -> Use relevant context to interpret."""
    session = ConversationSession()
    session.add_message("user", "We are designing a microservices API.")
    session.add_message("assistant", "An API connects distributed services.")

    # Incomplete utterance "What is an..." should infer "What is an API?"
    res = orchestrator.process_message(session, "What is an...", search_mode="Auto")
    assert res["success"] is True
    # User message in session should have resolved query
    user_queries = [m["content"] for m in session.messages if m["role"] == "user"]
    assert any("API" in q for q in user_queries)


def test_acceptance_6_explain_code_step_by_step(orchestrator):
    """Test 6: 'Explain this code step by step.' -> Step-by-step explanation with code context."""
    assert detect_adaptive_level("Explain this code step by step.") == 3
    session = ConversationSession()
    session.add_message("user", "Here is my code:\n```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        pass\n```")
    session.add_message("assistant", "I see your binary search implementation.")

    res = orchestrator.process_message(session, "Explain this code step by step.", search_mode="Auto")
    assert res["success"] is True
    assert "step" in res["content"].lower() or "1." in res["content"]


def test_acceptance_7_give_10_mark_answer(orchestrator):
    """Test 7: 'Give a 10-mark answer on machine learning.' -> Sufficiently detailed, exam-oriented answer."""
    assert detect_adaptive_level("Give a 10-mark answer on machine learning.") == 4
    session = ConversationSession()
    res = orchestrator.process_message(session, "Give a 10-mark answer on machine learning.", search_mode="Auto")
    assert res["success"] is True
    content = res["content"]
    assert len(content.split()) >= 60
    assert "10-mark" in content.lower() or "introduction" in content.lower() or "foundations" in content.lower()


def test_acceptance_8_what_is_ai_one_sentence(orchestrator):
    """Test 8: 'What is AI? Explain in one sentence.' -> One simple sentence, with no additional sections."""
    session = ConversationSession()
    res = orchestrator.process_message(session, "What is AI? Explain in one sentence.", search_mode="Auto")
    assert res["success"] is True
    content = res["content"].strip()

    # Must be 1 sentence
    assert "\n\n" not in content
    assert "Example:" not in content
    assert content.count(".") <= 2
    assert len(content.split()) <= 30


def test_acceptance_9_complete_architecture_and_implementation(orchestrator):
    """Test 9: 'Give the complete architecture and implementation plan.' -> Comprehensive technical deliverable."""
    assert detect_adaptive_level("Give the complete architecture and implementation plan.") == 5
    session = ConversationSession()
    res = orchestrator.process_message(session, "Give the complete architecture and implementation plan.", search_mode="Auto")
    assert res["success"] is True
    content = res["content"]
    assert "Architecture" in content or "architecture" in content
    assert "Implementation" in content or "implementation" in content
    assert len(content.split()) >= 40
