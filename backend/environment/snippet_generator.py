"""
Dynamic Code Snippet Generator
Uses OpenAI API to generate diverse, realistic code snippets with ground-truth bugs.
This replaces hardcoded examples and gives the environment infinite variety.
"""

import json
import random
import os
from openai import OpenAI
from typing import List, Optional
from .models import Bug, BugType, Severity, CodeSnippet


# ─── Prompt Templates ──────────────────────────────────────────────────────────

TASK1_PROMPT = """Generate a short Python code snippet (3-8 lines) for a code review task.

Requirements:
- EITHER has exactly 1 clear bug OR is completely clean code
- Must be realistic production-like code
- Bug types to use: {bug_types}
- Difficulty: easy (bugs should be somewhat obvious)

Return ONLY valid JSON, no markdown, no explanation:
{{
  "filename": "example.py",
  "code": "def foo():\\n    ...",
  "has_bugs": true,
  "bugs": [
    {{
      "line_number": 2,
      "bug_type": "security",
      "severity": "critical",
      "description": "What the bug is",
      "suggested_fix": "Exact code fix"
    }}
  ]
}}

If has_bugs is false, set bugs to [].
Pick a random scenario from: {scenarios}"""

TASK2_PROMPT = """Generate a Python code snippet (8-15 lines) with 2-3 bugs for a code review task.

Requirements:
- Must have EXACTLY {num_bugs} bugs
- Mix of bug types: {bug_types}
- Include at least one severity mismatch trap (make reviewer think about severity)
- Realistic production code from: {scenarios}

Return ONLY valid JSON, no markdown:
{{
  "filename": "example.py",
  "code": "...",
  "has_bugs": true,
  "bugs": [
    {{
      "line_number": <int>,
      "bug_type": "<type>",
      "severity": "<critical|high|medium|low|info>",
      "description": "<description>",
      "suggested_fix": "<exact fix>"
    }}
  ]
}}"""

TASK3_PROMPT = """Generate a Python code snippet (10-20 lines) with 1 complex architectural bug requiring a detailed fix.

Requirements:
- Bug should require meaningful refactoring or design change
- Should test understanding, not just syntax knowledge
- Scenario: {scenario}

Return ONLY valid JSON, no markdown:
{{
  "filename": "example.py", 
  "code": "...",
  "has_bugs": true,
  "bugs": [
    {{
      "line_number": <int>,
      "bug_type": "<logic|performance|race_condition|memory_leak|security>",
      "severity": "<critical|high>",
      "description": "<detailed description>",
      "suggested_fix": "<detailed fix with code example>"
    }}
  ]
}}"""

# ─── Scenarios for diversity ───────────────────────────────────────────────────

SCENARIOS = [
    "user authentication", "database query", "file upload handler",
    "REST API endpoint", "caching layer", "rate limiter",
    "password hashing", "session management", "data serialization",
    "async task queue", "payment processing", "email sender",
    "search functionality", "pagination", "data validation",
    "CSV parser", "JWT token handler", "webhook processor",
    "background job scheduler", "configuration loader"
]

BUG_TYPES = ["security", "logic", "performance", "best_practice", "race_condition", "memory_leak"]


# ─── Generator Class ───────────────────────────────────────────────────────────

class SnippetGenerator:
    """Generates diverse code snippets using OpenAI"""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key)
        self._cache: List[CodeSnippet] = []

    def generate(self, task_id: int, count: int = 1) -> List[CodeSnippet]:
        """Generate `count` snippets for the given task ID"""
        snippets = []
        for _ in range(count):
            snippet = self._generate_one(task_id)
            if snippet:
                snippets.append(snippet)
        return snippets

    def _generate_one(self, task_id: int) -> Optional[CodeSnippet]:
        """Generate a single snippet via OpenAI API"""
        try:
            if task_id == 1:
                prompt = TASK1_PROMPT.format(
                    bug_types=random.sample(BUG_TYPES, 3),
                    scenarios=random.sample(SCENARIOS, 4)
                )
            elif task_id == 2:
                num_bugs = random.choice([2, 3])
                prompt = TASK2_PROMPT.format(
                    num_bugs=num_bugs,
                    bug_types=random.sample(BUG_TYPES, 3),
                    scenarios=random.sample(SCENARIOS, 3)
                )
            else:
                prompt = TASK3_PROMPT.format(
                    scenario=random.choice(SCENARIOS)
                )

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=800,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code generation assistant. Return ONLY valid JSON, no markdown, no explanation."
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            return self._parse_snippet(data, task_id)

        except Exception as e:
            print(f"[SnippetGenerator] Error generating snippet: {e}")
            return None

    def _parse_snippet(self, data: dict, task_id: int) -> CodeSnippet:
        """Convert raw JSON into a CodeSnippet with Bug objects"""
        bugs = []
        for b in data.get("bugs", []):
            try:
                bugs.append(Bug(
                    line_number=b["line_number"],
                    bug_type=BugType(b["bug_type"]),
                    severity=Severity(b["severity"]),
                    description=b["description"],
                    suggested_fix=b.get("suggested_fix"),
                    confidence=0.95  # LLM-generated = high confidence ground truth
                ))
            except Exception as e:
                print(f"[SnippetGenerator] Bug parse error: {e}, raw: {b}")

        code_str = data.get("code", "")
        line_count = len(code_str.splitlines())

        return CodeSnippet(
            id=f"gen_task{task_id}_{random.randint(1000, 9999)}",
            filename=data.get("filename", "generated.py"),
            code=code_str,
            line_count=line_count,
            author="generated",
            known_bugs=bugs
        )