"""
AI Agent using OpenAI to interact with Code Review Environment
"""

import os
import json
from typing import Dict, List
from openai import OpenAI


class CodeReviewAgent:
    """AI Agent that uses OpenAI to review code"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("API_BASE_URL", "https://api.openai.com/v1")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        self.learning_memory: List[Dict] = []

    # =========================
    # 🚀 MAIN FUNCTION
    # =========================
    def analyze_code(self, code: str, task_description: str, task_id: int) -> Dict:
        """Analyze code and return structured response"""

        if task_id == 1:
            prompt = self._build_task1_prompt(code, task_description)
        elif task_id == 2:
            prompt = self._build_task2_prompt(code, task_description)
        else:
            prompt = self._build_task3_prompt(code, task_description)

        if self.learning_memory:
            prompt += self._add_learning_context()

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert code reviewer. "
                            "Return ONLY valid JSON. No explanations."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()

            return json.loads(content)

        except Exception as e:
            print(f"[ERROR] OpenAI call failed: {e}")
            return {
                "action_type": "skip",
                "issues": [],
                "suggestions": [],
                "confidence": 0.3
            }

    # =========================
    # 🧠 PROMPT BUILDERS
    # =========================

    def _build_task1_prompt(self, code: str, task_description: str) -> str:
        return f"""
Task: {task_description}

Code:
{code}

Find:
- Bugs
- Syntax errors
- Logical mistakes

Return JSON:
{{
  "action_type": "review",
  "issues": ["bug1", "bug2"],
  "confidence": 0.0
}}
""".strip()

    def _build_task2_prompt(self, code: str, task_description: str) -> str:
        return f"""
Task: {task_description}

Code:
{code}

Find:
- Security vulnerabilities
- Performance issues
- Bad coding practices

Return JSON:
{{
  "action_type": "review",
  "issues": ["issue1"],
  "suggestions": ["fix1"],
  "confidence": 0.0
}}
""".strip()

    def _build_task3_prompt(self, code: str, task_description: str) -> str:
        return f"""
Task: {task_description}

Code:
{code}

Perform deep review:
- Architecture problems
- Scalability issues
- Maintainability

Return JSON:
{{
  "action_type": "review",
  "issues": ["issue1"],
  "suggestions": ["improvement1"],
  "confidence": 0.0
}}
""".strip()

    # =========================
    # 🧠 LEARNING MEMORY
    # =========================

    def _add_learning_context(self) -> str:
        context = "\n\nPast Learnings:\n"
        for memory in self.learning_memory[-3:]:
            context += f"- {memory}\n"
        return context

    def update_memory(self, result: Dict):
        self.learning_memory.append(result)

if __name__ == "__main__":
    # 🔹 Sample test code
    sample_code = """
def divide(a, b):
    return a / b

print(divide(10, 0))
"""

    task_description = "Find bugs in the given Python code"
    task_id = 1

    try:
        agent = CodeReviewAgent()
        result = agent.analyze_code(sample_code, task_description, task_id)

        print("\n=== AGENT OUTPUT ===")
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}")