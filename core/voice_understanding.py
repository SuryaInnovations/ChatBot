"""
core/voice_understanding.py — Intelligent Voice Note Understanding & Clarification Engine.

Provides:
1. Speech transcript cleaning (removes filler words, stutters, and fixes common phonetic STT errors).
2. Incomplete sentence detection & conversational inference.
3. Polite, single-question clarification when meaning is genuinely ambiguous.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def clean_voice_transcript(text: str) -> str:
    """
    Cleans spoken audio transcription by removing conversational filler words,
    speech disfluencies (stutters), orphan punctuation, and correcting common STT phonetic slips.
    """
    if not text:
        return ""
    t = text.strip()
    # Preserve raw code blocks, multiline code/prompts, and explicit SQL/programming definitions untouched
    if "\n" in t or "```" in t or t.startswith(("def ", "class ", "import ", "from ", "SELECT ", "select ", "Debug ", "debug ")):
        return t

    # 1. Common Phonetic STT corrections for developer & technical terms
    phonetic_map = [
        (r'\bpie\s+thon\b', 'Python'),
        (r'\bpi\s+thon\b', 'Python'),
        (r'\ba\s+p\s+i\b', 'API'),
        (r'\bsequel\s+query\b', 'SQL query'),
        (r'\bsequel\s+database\b', 'SQL database'),
        (r'\bsequel\b', 'SQL'),
        (r'\breact\s+j\s*s\b', 'React.js'),
        (r'\bnode\s+j\s*s\b', 'Node.js'),
        (r'\bc\s+plus\s+plus\b', 'C++'),
        (r'\bc\s+sharp\b', 'C#'),
        (r'\btype\s+script\b', 'TypeScript'),
        (r'\bjava\s+script\b', 'JavaScript'),
        (r'\bpost\s+gres\b', 'PostgreSQL'),
        (r'\bpost\s+gre\s+sql\b', 'PostgreSQL'),
    ]
    for pattern, repl in phonetic_map:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # 2. Stutter & repetition removal (e.g., 'what what is', 'can can you')
    t = re.sub(r'\b([a-zA-Z]+)\s+\1\b', r'\1', t, flags=re.IGNORECASE)
    t = re.sub(r'\b([a-zA-Z]+)\s+\1\b', r'\1', t, flags=re.IGNORECASE)

    # 3. Filler words removal ('um', 'uh', 'you know', 'so yeah', leading 'like')
    fillers = [
        r'\b(um|uh|erm|er|ah|you know|so yeah|so uh|um yeah)\b',
        r'^[,\s]*(like|basically|actually|i mean|so)[,\s]+',
        r'[,\s]+(you know|um|uh|ah)\s*$'
    ]
    for f in fillers:
        t = re.sub(f, '', t, flags=re.IGNORECASE)

    # 4. Clean orphan commas, spaces, and punctuation
    t = re.sub(r'\s*,\s*([?.!])', r'\1', t)
    t = re.sub(r'\s*,\s*,+', ',', t)
    t = re.sub(r'^[,\s]+', '', t)
    t = re.sub(r'[,\s]+$', '', t)
    t = re.sub(r'[^\S\r\n]+', ' ', t).strip()

    # 5. Capitalize first letter while preserving casing of acronyms (API, SQL, etc.)
    if t:
        t = t[0].upper() + t[1:]
    return t


def is_incomplete_query(query: str) -> bool:
    """
    Detects if an utterance is cut off or grammatically incomplete
    (e.g., 'What is an...', 'What is a', 'How does...', 'Explain the...').
    """
    q = query.strip().lower()
    if not q:
        return True

    # Trailing ellipsis or trailing open prepositions/articles
    incomplete_patterns = [
        r'^(what|who|where|why|when|how)\s+(is|are|was|were|do|does|did|can|could|would|should)?\s*(a|an|the|about|to|of|in|for)?\s*(\.{2,})?$',
        r'^(tell|explain)\s+(me)?\s*(about)?\s*(a|an|the)?\s*(\.{2,})?$',
        r'^(can|could|would)\s+you\s+(tell|explain|show)\s+(me)?\s*(about)?\s*(a|an|the)?\s*(\.{2,})?$',
        r'.+\s+(is|are|a|an|the|of|to|in|for|about)\s*(\.{2,})$',
        r'^(what|how|why|who)\s+(is|are)\s*$'
    ]
    for p in incomplete_patterns:
        if re.match(p, q):
            return True
    return False


def extract_recent_topic(history: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """
    Inspects recent conversation turns to extract the active technical topic or subject noun.
    """
    if not history:
        return None

    # Scan last 4 messages in reverse order
    for msg in reversed(history[-4:]):
        content = msg.get("content", "")
        if not content:
            continue

        # 1. Technical acronyms with optional plural (e.g., API, APIs, SQL, REST, HTTP, JSON, SDK, LLM, GPU)
        acronyms = re.findall(
            r'\b(API|REST|SQL|JSON|HTTP|URL|HTML|CSS|SDK|CLI|ORM|DOM|LLM|GPU|CPU|NLP|RAG|AWS|GCP)s?\b',
            content,
            re.IGNORECASE
        )
        if acronyms:
            return acronyms[-1].upper()

        # 2. Prominent languages, frameworks, and CS concepts
        tech_matches = re.findall(
            r'\b(Python|FastAPI|Docker|Django|Flask|React|JavaScript|TypeScript|Kubernetes|GitHub|Linux|Rust|Java|Golang|Pandas|NumPy|PyTorch|TensorFlow|C\+\+|algorithm|database|recursion|binary search|linked list|sorting)\b',
            content,
            re.IGNORECASE
        )
        if tech_matches:
            return tech_matches[-1].title()

        # 3. Explicit definitions or subjects in questions (e.g. "What is X?", "Explain Y")
        q_match = re.search(
            r'(?:about|what is|explain|define|regarding)\s+(?:an?\s+|the\s+)?([a-zA-Z0-9_\-]{2,25})[?\.\n]?',
            content,
            re.IGNORECASE
        )
        if q_match:
            cand = q_match.group(1).strip()
            if cand.lower() not in ['this', 'that', 'it', 'me', 'you', 'something', 'anything']:
                cleaned = re.sub(r's$', '', cand, flags=re.IGNORECASE)
                return cleaned.upper() if len(cleaned) <= 4 else cleaned.title()

    return None


def resolve_incomplete_or_voice_query(
    query: str,
    history: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Resolves an incomplete query using conversation history:
    - If incomplete and active context topic is found: infers intended question (returns True, inferred_query, None).
    - If incomplete and no context topic: returns single short clarification (returns True, query, 'What would you like to know about?').
    - If complete: returns (False, query, None).
    """
    if not is_incomplete_query(query):
        return False, query, None

    topic = extract_recent_topic(history)
    if topic:
        q_clean = query.rstrip('. ').strip()

        # Grammatical article alignment ('a' vs 'an')
        is_vowel = topic[0].lower() in 'aeiou'
        if q_clean.lower().endswith(' an') and not is_vowel:
            q_clean = q_clean[:-3] + ' a'
        elif q_clean.lower().endswith(' a') and is_vowel:
            q_clean = q_clean[:-2] + ' an'

        inferred = f"{q_clean} {topic}?"
        return True, inferred, None

    # No context: polite, direct clarification without generic error messages
    clarification = "What would you like to know about?"
    return True, query, clarification
