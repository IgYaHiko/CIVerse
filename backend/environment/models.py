"""
Code Review Environment - Type Models
All data structures are Pydantic models for OpenEnv compliance
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

# ============ Enums ============

class Severity(str, Enum):
    """Bug severity levels"""
    CRITICAL = "critical"      # Security, crashes, data loss
    HIGH = "high"              # Logic errors, broken features
    MEDIUM = "medium"          # Performance, edge cases
    LOW = "low"                # Style, minor issues
    INFO = "info"              # Suggestions, improvements

class BugType(str, Enum):
    """Types of bugs/issues"""
    SECURITY = "security"           # SQL injection, XSS, etc.
    LOGIC = "logic"                 # Wrong conditions, off-by-one
    PERFORMANCE = "performance"     # Inefficient code
    STYLE = "style"                 # PEP8, naming conventions
    DOCUMENTATION = "documentation" # Missing docs, unclear
    BEST_PRACTICE = "best_practice" # Not following best practices
    RACE_CONDITION = "race_condition"
    MEMORY_LEAK = "memory_leak"

class ActionType(str, Enum):
    """Actions the AI agent can take"""
    DETECT_BUG = "detect_bug"
    CLASSIFY_SEVERITY = "classify_severity"
    SUGGEST_FIX = "suggest_fix"
    REVIEW = "review"
    EXPLAIN = "explain"
    SKIP = "skip"

# ============ Core Models ============

class Bug(BaseModel):
    """A single bug/issue in code"""
    line_number: int
    bug_type: BugType
    severity: Severity
    description: str
    suggested_fix: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    class Config:
        use_enum_values = True

class CodeSnippet(BaseModel):
    """Code to be reviewed"""
    id: str
    filename: str
    language: str = "python"
    code: str
    line_count: int
    author: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    complexity: Optional[float] = Field(None, ge=1.0, le=10.0)
    known_bugs: List[Bug] = []  # Ground truth for grading
    
    class Config:
        use_enum_values = True

class CodeReviewContext(BaseModel):
    """Full context for the current review"""
    code: CodeSnippet
    task_id: int
    difficulty: str
    description: str
    max_steps: int
    current_step: int
    bugs_found: List[Bug] = []
    attempts: int = 0

class Action(BaseModel):
    """Action taken by the AI agent"""
    action_type: ActionType
    bug: Optional[Bug] = None
    bug_type: Optional[BugType] = None
    severity: Optional[Severity] = None
    line_number: Optional[int] = None
    fix_suggestion: Optional[str] = None
    explanation: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    class Config:
        use_enum_values = True

class Observation(BaseModel):
    """What the agent sees"""
    code_context: CodeReviewContext
    available_actions: List[str]
    current_task: int
    task_description: str
    step_count: int
    max_steps: int
    bugs_found_so_far: int = 0
    total_bugs: int = 0

class Reward(BaseModel):
    """Reward with detailed breakdown"""
    score: float = Field(ge=0.0, le=1.0)
    breakdown: Dict[str, float]
    feedback: str
    bugs_correctly_found: int = 0
    bugs_missed: int = 0
    false_positives: int = 0

class EnvironmentState(BaseModel):
    """Full environment state"""
    current_task: int
    step_count: int
    total_score: float
    tasks_completed: List[int]
    current_code_id: str
    bugs_found: List[Bug]
    actions_taken: List[Action]