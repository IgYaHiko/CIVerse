"""
OpenAI-Powered Code Review Agent
Bridges LLM output → structured Action objects for the environment.

This is the KEY fix from v1: the agent now returns proper Action objects
that the environment can grade, not just raw JSON strings.
"""

import json
import re
import os
from openai import OpenAI
from typing import Dict, List, Optional, Tuple

# Import from environment package (adjust path as needed)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.models import Action, ActionType, Bug, BugType, Severity


# ─── Prompt Templates ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Python code reviewer participating in a structured evaluation.
You must analyze code and return ONLY valid JSON matching the exact schema requested.
Do not include markdown, explanations, or any text outside the JSON object."""

TASK1_PROMPT = """Analyze this Python code for bugs.

Code from file '{filename}':
```python
{code}
```

Task: {task_description}

If you find a bug, return:
{{
  "action_type": "detect_bug",
  "has_bug": true,
  "bug": {{
    "line_number": <int>,
    "bug_type": "<security|logic|performance|best_practice|race_condition|memory_leak|style|documentation>",
    "severity": "<critical|high|medium|low|info>",
    "description": "<clear description of the bug>",
    "suggested_fix": "<how to fix it>"
  }},
  "confidence": <0.0-1.0>,
  "explanation": "<brief reasoning>"
}}

If code is clean (no bugs), return:
{{
  "action_type": "skip",
  "has_bug": false,
  "bug": null,
  "confidence": <0.0-1.0>,
  "explanation": "<why code is clean>"
}}

Return ONLY the JSON object."""

TASK2_PROMPT = """Analyze this Python code and find ALL bugs.

Code from file '{filename}':
```python
{code}
```

Task: {task_description}
Bugs found so far: {bugs_found}

Find the NEXT bug you haven't reported yet, or confirm all bugs are found.

Return:
{{
  "action_type": "detect_bug",
  "bug": {{
    "line_number": <int>,
    "bug_type": "<security|logic|performance|best_practice|race_condition|memory_leak|style|documentation>",
    "severity": "<critical|high|medium|low|info>",
    "description": "<description>",
    "suggested_fix": "<fix>"
  }},
  "confidence": <0.0-1.0>,
  "all_bugs_found": <true|false>,
  "explanation": "<reasoning>"
}}

Return ONLY the JSON object."""

TASK3_PROMPT = """Analyze this Python code and suggest a detailed fix for the main bug.

Code from file '{filename}':
```python
{code}
```

Task: {task_description}

Provide a thorough fix suggestion with code example.

Return:
{{
  "action_type": "suggest_fix",
  "bug": {{
    "line_number": <int>,
    "bug_type": "<security|logic|performance|best_practice|race_condition|memory_leak|style|documentation>",
    "severity": "<critical|high>",
    "description": "<detailed bug description>",
    "suggested_fix": "<exact code showing the fix>"
  }},
  "fix_suggestion": "<detailed fix with code example>",
  "explanation": "<why this fix works, what problem it solves>",
  "confidence": <0.0-1.0>
}}

Return ONLY the JSON object."""


# ─── Agent Class ──────────────────────────────────────────────────────────────

class CodeReviewAgent:
    """
    OpenAI-powered agent that converts LLM output to proper Action objects.

    This solves the critical Action format mismatch from v1.
    The agent's act() now returns Action objects, not raw dicts.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key)
        self.model = model
        self.learning_memory: List[Dict] = []
        self.total_calls = 0
        self.total_score = 0.0

    # ─── Main API ─────────────────────────────────────────────────────────────

    def act(self, observation) -> Action:
        """
        Main method: takes an Observation, returns a valid Action.
        This is the correct interface with the environment.
        """
        code = observation.code_context.code.code
        filename = observation.code_context.code.filename
        task_id = observation.current_task
        task_desc = observation.task_description
        bugs_found = observation.bugs_found_so_far

        raw_response = self._call_llm(code, filename, task_id, task_desc, bugs_found)
        action = self._parse_to_action(raw_response, task_id)
        return action

    def update_from_reward(self, reward, info: Dict):
        """Call after each step to update learning memory"""
        self.total_calls += 1
        self.total_score = (self.total_score * (self.total_calls - 1) + reward.score) / self.total_calls

        # Store feedback for future context (last 5 only)
        memory_entry = {
            'score': reward.score,
            'feedback': reward.feedback,
            'task': info.get('task_name', ''),
        }
        self.learning_memory.append(memory_entry)
        if len(self.learning_memory) > 5:
            self.learning_memory.pop(0)

    # ─── OpenAI API Call ──────────────────────────────────────────────────────

    def _call_llm(self, code: str, filename: str, task_id: int,
                     task_desc: str, bugs_found: int) -> Dict:
        """Call OpenAI API and return parsed JSON"""
        if task_id == 1:
            prompt = TASK1_PROMPT.format(
                filename=filename, code=code, task_description=task_desc
            )
        elif task_id == 2:
            prompt = TASK2_PROMPT.format(
                filename=filename, code=code,
                task_description=task_desc, bugs_found=bugs_found
            )
        else:
            prompt = TASK3_PROMPT.format(
                filename=filename, code=code, task_description=task_desc
            )

        # Add learning context from past feedback
        if self.learning_memory:
            context = "\n\nPast performance (learn from this):\n"
            for m in self.learning_memory[-3:]:
                context += f"- [{m['task']}] Score: {m['score']:.2f} | Feedback: {m['feedback']}\n"
            prompt += context

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=600,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )

            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if model adds them
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

            return json.loads(raw.strip())

        except json.JSONDecodeError as e:
            print(f"[Agent] JSON parse error: {e}")
            return {"action_type": "skip", "confidence": 0.0, "explanation": f"JSON parse error: {e}"}
        except Exception as e:
            print(f"[Agent] API error: {e}")
            return {"action_type": "skip", "confidence": 0.0, "explanation": f"API error: {str(e)}"}

    # ─── Action Converter (THE BRIDGE) ────────────────────────────────────────

    def _parse_to_action(self, data: Dict, task_id: int) -> Action:
        """
        Convert raw LLM JSON → proper Action object.
        This is the critical bridge that was missing in v1.
        """
        if not data or not isinstance(data, dict):
            return Action(action_type=ActionType.SKIP, confidence=0.0, explanation="Invalid or empty data from LLM")

        action_type_str = data.get("action_type", "skip").lower()

        # Map to ActionType enum
        type_map = {
            "detect_bug": ActionType.DETECT_BUG,
            "suggest_fix": ActionType.SUGGEST_FIX,
            "classify_severity": ActionType.CLASSIFY_SEVERITY,
            "explain": ActionType.EXPLAIN,
            "review": ActionType.DETECT_BUG,  # Map legacy "review" → detect_bug
            "skip": ActionType.SKIP,
        }
        action_type = type_map.get(action_type_str, ActionType.SKIP)

        # Parse bug if present
        bug = None
        raw_bug = data.get("bug")
        if raw_bug and isinstance(raw_bug, dict) and action_type != ActionType.SKIP:
            try:
                # Ensure values match BugType and Severity enums
                bug_type_val = raw_bug.get("bug_type", "logic").lower()
                try:
                    BugType(bug_type_val)
                except ValueError:
                    bug_type_val = "logic"

                severity_val = raw_bug.get("severity", "medium").lower()
                try:
                    Severity(severity_val)
                except ValueError:
                    severity_val = "medium"

                bug = Bug(
                    line_number=int(raw_bug.get("line_number", 1)),
                    bug_type=BugType(bug_type_val),
                    severity=Severity(severity_val),
                    description=raw_bug.get("description", "No description"),
                    suggested_fix=raw_bug.get("suggested_fix"),
                    confidence=float(data.get("confidence", 0.8))
                )
            except (ValueError, KeyError, TypeError) as e:
                print(f"[Agent] Bug parse error: {e}, raw: {raw_bug}")
                # Fall back to skip if bug parsing fails
                action_type = ActionType.SKIP
                bug = None

        return Action(
            action_type=action_type,
            bug=bug,
            fix_suggestion=data.get("fix_suggestion"),
            explanation=data.get("explanation"),
            confidence=float(data.get("confidence", 0.8))
        )