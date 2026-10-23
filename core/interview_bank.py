"""
Curated Technical and Behavioral Interview Question Bank.
Indexed by role, category, company, and difficulty.
"""

from typing import List, Dict, Any, Optional
import random

INTERVIEW_QUESTION_BANK: List[Dict[str, Any]] = [
    # 1. DSA (Data Structures & Algorithms)
    {
        "id": "dsa-01",
        "role": "Software Engineer",
        "category": "DSA",
        "company": "Google",
        "difficulty": "Medium",
        "title": "Longest Substring Without Repeating Characters",
        "question": "Given a string `s`, find the length of the longest substring without repeating characters. What is the optimal time and space complexity?",
        "topic": "Sliding Window",
        "key_points": ["Sliding window with two pointers", "Hash map/set tracking indices", "O(N) time and O(min(N, Alphabet)) space"]
    },
    {
        "id": "dsa-02",
        "role": "Software Engineer",
        "category": "DSA",
        "company": "Amazon",
        "difficulty": "Medium",
        "title": "LRU Cache Implementation",
        "question": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache. How do you achieve O(1) get and put operations?",
        "topic": "Hash Map & Doubly Linked List",
        "key_points": ["Doubly linked list for ordering", "Hash map for O(1) key-to-node lookup", "Handling capacity evictions"]
    },
    {
        "id": "dsa-03",
        "role": "Software Engineer",
        "category": "DSA",
        "company": "Meta",
        "difficulty": "Hard",
        "title": "Median of Two Sorted Arrays",
        "question": "Given two sorted arrays `nums1` and `nums2` of size m and n respectively, return the median of the two sorted arrays in O(log(m+n)) runtime.",
        "topic": "Binary Search",
        "key_points": ["Binary search on smaller array partition", "Balancing left and right partitions", "Edge cases with odd/even total lengths"]
    },

    # 2. SQL & DATA
    {
        "id": "sql-01",
        "role": "Data Engineer",
        "category": "SQL",
        "company": "Amazon",
        "difficulty": "Medium",
        "title": "Top N Salaries per Department",
        "question": "Given an `Employee(id, name, salary, department_id)` table, write a SQL query to find the top 2 highest-paid employees in each department. How do you handle ties?",
        "topic": "Window Functions",
        "key_points": ["DENSE_RANK() over PARTITION BY department_id ORDER BY salary DESC", "Filtering rank <= 2 in CTE or subquery"]
    },
    {
        "id": "sql-02",
        "role": "Data Engineer",
        "category": "SQL",
        "company": "Uber",
        "difficulty": "Hard",
        "title": "User Retention and Churn Analysis",
        "question": "Write a query to calculate Month-over-Month retention rate of drivers who took at least 1 trip in their initial signup month.",
        "topic": "Cohort Retention",
        "key_points": ["Cohort grouping by DATE_TRUNC('month', signup_date)", "Self-join on active trips in subsequent months", "Calculating percentage active"]
    },

    # 3. MACHINE LEARNING & DATA SCIENCE
    {
        "id": "ml-01",
        "role": "Machine Learning Engineer",
        "category": "ML",
        "company": "Meta",
        "difficulty": "Medium",
        "title": "Handling Severe Class Imbalance",
        "question": "You are building a fraud detection model where only 0.1% of transactions are fraudulent. How would you choose your loss function, sampling strategy, and evaluation metrics?",
        "topic": "Classification & Imbalance",
        "key_points": ["PR-AUC / F1 instead of Accuracy or ROC-AUC", "Focal Loss or Class-weighted Cross-Entropy", "SMOTE or under-sampling negatives"]
    },
    {
        "id": "ml-02",
        "role": "Machine Learning Engineer",
        "category": "ML",
        "company": "Google",
        "difficulty": "Hard",
        "title": "Self-Attention Mechanism & KV Cache",
        "question": "Explain mathematically how Scaled Dot-Product Attention works. Why is KV Caching required during LLM autoregressive inference, and what is its memory cost?",
        "topic": "Transformers & LLMs",
        "key_points": ["Softmax(QK^T / sqrt(d_k)) * V", "Avoiding recomputing past token key/value projections", "Memory = 2 * layers * heads * head_dim * seq_len * precision"]
    },

    # 4. SYSTEM DESIGN
    {
        "id": "sd-01",
        "role": "Software Engineer",
        "category": "System Design",
        "company": "Netflix",
        "difficulty": "Medium",
        "title": "Design a Scalable URL Shortener (Bitly)",
        "question": "Design a URL shortening service that generates short aliases for long URLs. Walk through the capacity estimations, API design, database schema, and high-availability caching strategy.",
        "topic": "Distributed Systems",
        "key_points": ["Base62 encoding of counter or UUID hash", "Redis read-through cache for popular links", "NoSQL / Key-Value DB partitioned by hash"]
    },
    {
        "id": "sd-02",
        "role": "Software Engineer",
        "category": "System Design",
        "company": "Uber",
        "difficulty": "Hard",
        "title": "Design a Real-Time Ride Matching Dispatcher",
        "question": "Design the ride dispatch service for Uber. How do you ingest continuous GPS pings from drivers, query nearby available drivers within 2km in under 100ms, and prevent double-dispatch?",
        "topic": "Geospatial Indexing",
        "key_points": ["Geohash / Google S2 / Uber H3 spatial index", "Redis Pub/Sub or Kafka stream for location pings", "Distributed locks for atomic driver assignment"]
    },

    # 5. BEHAVIORAL & HR (STAR)
    {
        "id": "hr-01",
        "role": "All Roles",
        "category": "Behavioral",
        "company": "Amazon",
        "difficulty": "Medium",
        "title": "Disagree and Commit / Technical Disagreement",
        "question": "Tell me about a time you strongly disagreed with an engineering decision or product direction proposed by a team lead or colleague. How did you handle the discussion, and what was the outcome?",
        "topic": "Conflict Resolution",
        "key_points": ["STAR structure (Situation, Task, Action, Result)", "Focus on objective data/benchmarks rather than opinions", "Demonstrating professionalism and alignment"]
    },
    {
        "id": "hr-02",
        "role": "All Roles",
        "category": "Behavioral",
        "company": "Google",
        "difficulty": "Medium",
        "title": "Navigating Ambiguity and Unexpected Outage",
        "question": "Describe a situation where a production incident occurred or requirements changed drastically right before a deadline. What steps did you take to triage and deliver?",
        "topic": "Ownership & Crisis Management",
        "key_points": ["Immediate containment and stakeholder communication", "Root-cause analysis post-mortem", "Preventative guardrails implemented"]
    }
]


def get_questions_by_category(category: str) -> List[Dict[str, Any]]:
    """Returns questions matching a category (DSA, SQL, ML, System Design, Behavioral)."""
    cat_lower = category.lower()
    return [q for q in INTERVIEW_QUESTION_BANK if cat_lower in q["category"].lower() or cat_lower in q["role"].lower()]


def get_random_question(category: Optional[str] = None, difficulty: Optional[str] = None, company: Optional[str] = None) -> Dict[str, Any]:
    """Selects a question from the question bank matching filters, or random default."""
    candidates = INTERVIEW_QUESTION_BANK
    if category:
        cat_lower = category.lower()
        candidates = [q for q in candidates if cat_lower in q["category"].lower() or cat_lower in q["role"].lower()]
    if difficulty:
        diff_lower = difficulty.lower()
        candidates = [q for q in candidates if diff_lower == q["difficulty"].lower()]
    if company:
        comp_lower = company.lower()
        candidates = [q for q in candidates if comp_lower in q["company"].lower()]

    if not candidates:
        candidates = INTERVIEW_QUESTION_BANK

    return random.choice(candidates)


get_interview_question = get_random_question
get_questions_by_topic = get_questions_by_category
