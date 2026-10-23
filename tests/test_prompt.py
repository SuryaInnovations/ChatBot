"""
Unit tests for SPARK-AI master prompt and length mode detection.
"""

from core.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
    detect_length_mode,
    detect_adaptive_level,
    render_prompt,
    get_system_prompt,
    MASTER_SYSTEM_PROMPT
)


def test_system_prompt_template_sections():
    """Verify all 7 mandatory sections exist in the master prompt template."""
    assert "You are SPARK-AI" in SYSTEM_PROMPT_TEMPLATE
    assert "# 1. Response length and style" in SYSTEM_PROMPT_TEMPLATE
    assert "# 2. Task behavior" in SYSTEM_PROMPT_TEMPLATE
    assert "# 3. Accuracy and honesty" in SYSTEM_PROMPT_TEMPLATE
    assert "# 4. Tools" in SYSTEM_PROMPT_TEMPLATE
    assert "# 5. Security and privacy" in SYSTEM_PROMPT_TEMPLATE
    assert "# 6. Safety" in SYSTEM_PROMPT_TEMPLATE
    assert "# 7. User context (may be empty)" in SYSTEM_PROMPT_TEMPLATE
    assert "{length_mode}" in SYSTEM_PROMPT_TEMPLATE
    assert "{user_context}" in SYSTEM_PROMPT_TEMPLATE


def test_detect_length_mode():
    """Verify dynamic detection of length modes."""
    # Default is concise
    assert detect_length_mode("What is quantum computing?") == "concise"
    assert detect_length_mode("Give 2 topics for a research paper") == "concise"
    
    # Concise explicit
    assert detect_length_mode("Keep it brief and short") == "concise"
    assert detect_length_mode("Give a simple 3 line explanation") == "concise"

    # Study triggers
    assert detect_length_mode("Can you give me a quiz on binary search?") == "study"
    assert detect_length_mode("Create flashcards for machine learning") == "study"
    assert detect_length_mode("Test my knowledge on SQL joins") == "study"

    # Detailed triggers
    assert detect_length_mode("Explain in detail how backpropagation works") == "detailed"
    assert detect_length_mode("Provide step by step instructions for setting up Docker") == "detailed"
    assert detect_length_mode("Do a deep dive into Transformer architectures") == "detailed"


def test_render_prompt_substitution():
    """Verify template variables are substituted."""
    rendered = render_prompt(
        length_mode="detailed",
        user_context="User is learning calculus."
    )
    assert "- Current length mode: detailed" in rendered
    assert "User is learning calculus." in rendered
    assert "{length_mode}" not in rendered
    assert "{user_context}" not in rendered


def test_get_system_prompt():
    """Verify get_system_prompt aggregates custom directives and context."""
    prompt = get_system_prompt(
        custom_instructions="Always answer in bullet points.",
        user_context="Student level: Grade 12",
        length_mode="study"
    )
    assert "- Current length mode: study" in prompt
    assert "Student level: Grade 12" in prompt
    assert "Custom directives: Always answer in bullet points." in prompt
    assert "Current date and time:" in prompt


def test_master_system_prompt_default():
    """Verify default MASTER_SYSTEM_PROMPT is populated cleanly."""
    assert "- Current length mode: concise" in MASTER_SYSTEM_PROMPT
    assert "{length_mode}" not in MASTER_SYSTEM_PROMPT
    assert "{user_context}" not in MASTER_SYSTEM_PROMPT


def test_detect_adaptive_level():
    """Verify 5-level adaptive response detection."""
    # Level 1: Direct answer
    assert detect_adaptive_level("What is AI?") == 1
    assert detect_adaptive_level("What is an API?") == 1
    assert detect_adaptive_level("What is AI? Explain in one sentence.") == 1

    # Level 2: Beginner explanation
    assert detect_adaptive_level("Explain to a beginner how a database works") == 2
    assert detect_adaptive_level("How does this work?") == 2

    # Level 3: Step-by-step solution
    assert detect_adaptive_level("Explain this code step by step.") == 3
    assert detect_adaptive_level("Solve this step-by-step") == 3

    # Level 4: Detailed technical explanation
    assert detect_adaptive_level("Explain AI in detail.") == 4
    assert detect_adaptive_level("Do a deep dive into neural networks") == 4
    assert detect_adaptive_level("Give a 10-mark answer on machine learning.") == 4

    # Level 5: Complete deliverable
    assert detect_adaptive_level("Give the complete architecture and implementation plan.") == 5
    assert detect_adaptive_level("Provide a full system design for an e-commerce platform") == 5
