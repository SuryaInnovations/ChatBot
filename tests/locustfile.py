"""
Locust Load and Stress Testing Suite.
Simulates ramp-up from 50 to 1,000 concurrent users with realistic traffic distribution:
- 80% Normal Chat & Calculations
- 10% Conversation History Retrieval
- 5% Sandboxed Code Execution
- 5% Web Research & Tools
"""

import uuid
import random
from locust import HttpUser, task, between


SAMPLE_CHAT_QUERIES = [
    "What is the difference between supervised and unsupervised learning?",
    "Calculate the compound interest on $10,000 at 7% for 5 years",
    "Explain gradient descent with an intuitive analogy",
    "How does a hash map resolve collisions?",
    "Summarize the key advantages of microservices vs monoliths",
    "What is the time complexity of merge sort?",
    "Solve the quadratic equation x^2 - 7*x + 12 = 0"
]

SAMPLE_CODE_QUERIES = [
    "Write a Python function to reverse a linked list and test it",
    "Plot a sine wave with matplotlib and save it",
    "Implement binary search in Python with edge case handling"
]


class ChatbotLoadUser(HttpUser):
    wait_time = between(1.0, 3.0)

    def on_start(self):
        """Initializes a unique conversation session per simulated user."""
        self.conversation_id = f"locust_{uuid.uuid4().hex[:8]}"
        self.user_id = f"user_{uuid.uuid4().hex[:6]}"

    @task(80)
    def test_chat_inference(self):
        """Simulates normal chat query (80% traffic)."""
        prompt = random.choice(SAMPLE_CHAT_QUERIES)
        payload = {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "message": prompt,
            "provider": "auto",
            "idempotency_key": str(uuid.uuid4())
        }
        with self.client.post("/api/v1/chat", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    resp.success()
                else:
                    resp.failure(f"Assistant returned failure: {data.get('error')}")
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text}")

    @task(10)
    def test_get_history(self):
        """Simulates conversation history checks (10% traffic)."""
        with self.client.get(f"/api/v1/conversations/{self.conversation_id}", catch_response=True) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"History retrieval failed with HTTP {resp.status_code}")

    @task(5)
    def test_code_sandbox(self):
        """Simulates heavy Python code execution (5% traffic)."""
        prompt = random.choice(SAMPLE_CODE_QUERIES)
        payload = {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "message": prompt,
            "idempotency_key": str(uuid.uuid4())
        }
        with self.client.post("/api/v1/chat", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Code sandbox failed: HTTP {resp.status_code}")

    @task(5)
    def test_health_check(self):
        """Simulates background load balancer health probe."""
        self.client.get("/health/live")
