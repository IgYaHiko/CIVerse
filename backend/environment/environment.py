"""
Code Review Environment - Main Implementation
Full OpenEnv API: step(), reset(), state()
"""

import random
from typing import Tuple, List, Dict, Optional
from .models import (
    CodeSnippet, CodeReviewContext, Action, Observation, 
    Reward, EnvironmentState, Bug, BugType, Severity, ActionType
)
from .tasks import BugDetectionGrader, BugClassificationGrader, FixSuggestionGrader

class CodeReviewEnvironment:
    """Complete OpenEnv-compliant code review environment"""
    
    def __init__(self):
        """Initialize environment with code examples for each task"""
        self._init_task_data()
        self.reset()
    
    def _init_task_data(self):
        """Initialize code snippets for all 3 tasks"""
        
        # Task 1: Easy - Simple bug detection
        self.task1_codes = [
            # SQL Injection vulnerability
            CodeSnippet(
                id="task1_1",
                filename="user_auth.py",
                code="""def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)""",
                line_count=3,
                author="developer1",
                known_bugs=[
                    Bug(
                        line_number=2,
                        bug_type=BugType.SECURITY,
                        severity=Severity.CRITICAL,
                        description="SQL injection vulnerability",
                        suggested_fix="Use parameterized queries: db.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
                    )
                ]
            ),
            # Clean code with no bugs
            CodeSnippet(
                id="task1_2",
                filename="utils.py",
                code="""def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)""",
                line_count=4,
                author="developer2",
                known_bugs=[]
            ),
            # XSS vulnerability
            CodeSnippet(
                id="task1_3",
                filename="render.py",
                code="""def render_html(content):
    return f"<div>{content}</div>" """,
                line_count=2,
                author="developer3",
                known_bugs=[
                    Bug(
                        line_number=1,
                        bug_type=BugType.SECURITY,
                        severity=Severity.HIGH,
                        description="XSS vulnerability - content not escaped",
                        suggested_fix="Use html.escape(content) or template engine with auto-escaping"
                    )
                ]
            ),
        ]
        
        # Task 2: Medium - Multiple bugs to find
        self.task2_codes = [
            CodeSnippet(
                id="task2_1",
                filename="data_processor.py",
                code="""def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result""",
                line_count=5,
                author="developer1",
                known_bugs=[
                    Bug(
                        line_number=2,
                        bug_type=BugType.PERFORMANCE,
                        severity=Severity.MEDIUM,
                        description="Inefficient - should use list comprehension",
                        suggested_fix="result = [x * 2 for x in data if x > 0]"
                    ),
                    Bug(
                        line_number=3,
                        bug_type=BugType.LOGIC,
                        severity=Severity.MEDIUM,
                        description="Potential index error if data is None",
                        suggested_fix="Add None check: if data is None: return []"
                    )
                ]
            ),
            CodeSnippet(
                id="task2_2",
                filename="api_handler.py",
                code="""def fetch_user_data(user_id):
    response = requests.get(f'/api/users/{user_id}')
    if response.status == 200:
        return response.json()
    return None""",
                line_count=5,
                author="developer2",
                known_bugs=[
                    Bug(
                        line_number=2,
                        bug_type=BugType.SECURITY,
                        severity=Severity.HIGH,
                        description="No timeout set on request - could hang",
                        suggested_fix="Add timeout: requests.get(..., timeout=5)"
                    ),
                    Bug(
                        line_number=3,
                        bug_type=BugType.BEST_PRACTICE,
                        severity=Severity.LOW,
                        description="Should check status_code, not status",
                        suggested_fix="response.status_code == 200"
                    )
                ]
            )
        ]
        
        # Task 3: Hard - Complex bug requiring fix
        self.task3_codes = [
            CodeSnippet(
                id="task3_1",
                filename="cache.py",
                code="""class Cache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            # Remove oldest item (but this doesn't track order!)
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = value""",
                line_count=13,
                author="developer1",
                known_bugs=[
                    Bug(
                        line_number=12,
                        bug_type=BugType.LOGIC,
                        severity=Severity.HIGH,
                        description="Cache eviction doesn't track order - removes arbitrary item",
                        suggested_fix="Use OrderedDict or collections.deque to track insertion order"
                    )
                ]
            )
        ]
    
    def reset(self) -> Observation:
        """Reset environment to start of Task 1"""
        self.current_task = 1
        self.current_code_index = 0
        self.step_count = 0
        self.total_score = 0.0
        self.tasks_completed = []
        self.bugs_found = []
        self.actions_taken = []
        self.done = False
        
        return self._get_observation()
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, dict]:
        """Execute action and return next state"""
        if self.done:
            raise RuntimeError("Episode finished. Call reset() first.")
        
        # Store action
        self.actions_taken.append(action)
        self.step_count += 1
        
        # Get current code and task
        current_code = self._get_current_code()
        task_config = self._get_task_config()
        
        # Grade the action
        grader = task_config['grader']
        grade_result = grader.grade(
            current_code.known_bugs,
            action,
            {'bugs_found': self.bugs_found, 'target_bug': action.bug}
        )
        
        # Update found bugs if this was a detection
        if action.action_type == ActionType.DETECT_BUG and action.bug:
            # Check if this bug hasn't been found before
            already_found = any(
                b.line_number == action.bug.line_number and b.bug_type == action.bug.bug_type
                for b in self.bugs_found
            )
            if not already_found:
                self.bugs_found.append(action.bug)
        
        # Calculate reward
        reward_score = grade_result['score']
        
        # Update total score (running average)
        total_actions = len(self.actions_taken)
        self.total_score = (self.total_score * (total_actions - 1) + reward_score) / total_actions
        
        # Create reward object
        reward = Reward(
            score=reward_score,
            breakdown=grade_result.get('breakdown', {}),
            feedback=grade_result['feedback'],
            bugs_correctly_found=grade_result.get('breakdown', {}).get('bugs_found', 0),
            bugs_missed=len(current_code.known_bugs) - grade_result.get('breakdown', {}).get('bugs_found', 0),
            false_positives=0
        )
        
        # Check if task is complete
        task_complete = self._is_task_complete(task_config)
        info = {
            'task_complete': task_complete,
            'task_id': self.current_task,
            'task_name': task_config['name'],
            'steps_remaining': task_config['max_steps'] - self.step_count,
            'total_score': self.total_score
        }
        
        # Move to next task if complete
        if task_complete:
            self.tasks_completed.append(self.current_task)
            if self.current_task < 3:
                self.current_task += 1
                self.current_code_index = 0
                self.step_count = 0
                self.bugs_found = []
            else:
                self.done = True
        
        observation = self._get_observation()
        
        return observation, reward, self.done, info
    
    def state(self) -> EnvironmentState:
        """Return current environment state"""
        return EnvironmentState(
            current_task=self.current_task,
            step_count=self.step_count,
            total_score=self.total_score,
            tasks_completed=self.tasks_completed,
            current_code_id=self._get_current_code().id,
            bugs_found=self.bugs_found,
            actions_taken=self.actions_taken
        )
    
    def _get_current_code(self) -> CodeSnippet:
        """Get current code snippet based on task and index"""
        if self.current_task == 1:
            return self.task1_codes[self.current_code_index % len(self.task1_codes)]
        elif self.current_task == 2:
            return self.task2_codes[self.current_code_index % len(self.task2_codes)]
        else:
            return self.task3_codes[self.current_code_index % len(self.task3_codes)]
    
    def _get_task_config(self) -> Dict:
        """Get configuration for current task"""
        tasks = {
            1: {
                'name': 'Bug Detection',
                'description': 'Detect if there are bugs in this code. Use DETECT_BUG action.',
                'grader': BugDetectionGrader(),
                'max_steps': 2,
                'difficulty': 'easy'
            },
            2: {
                'name': 'Bug Classification',
                'description': 'Find ALL bugs and classify their severity correctly.',
                'grader': BugClassificationGrader(),
                'max_steps': 5,
                'difficulty': 'medium'
            },
            3: {
                'name': 'Fix Suggestion',
                'description': 'Suggest a fix for the bug with explanation.',
                'grader': FixSuggestionGrader(),
                'max_steps': 3,
                'difficulty': 'hard'
            }
        }
        return tasks[self.current_task]
    
    def _is_task_complete(self, task_config: Dict) -> bool:
        """Check if current task is complete"""
        current_code = self._get_current_code()
        
        if self.current_task == 1:
            # Task 1: Need to detect if bugs exist
            has_detected = any(
                a.action_type == ActionType.DETECT_BUG or 
                (a.action_type == ActionType.SKIP and len(current_code.known_bugs) == 0)
                for a in self.actions_taken
            )
            return has_detected or self.step_count >= task_config['max_steps']
        
        elif self.current_task == 2:
            # Task 2: Need to find all bugs
            bugs_found_count = len(self.bugs_found)
            total_bugs = len(current_code.known_bugs)
            return bugs_found_count >= total_bugs or self.step_count >= task_config['max_steps']
        
        else:
            # Task 3: Need to suggest fix
            has_suggested = any(a.action_type == ActionType.SUGGEST_FIX for a in self.actions_taken)
            return has_suggested or self.step_count >= task_config['max_steps']
    
    def _get_observation(self) -> Observation:
        """Build observation object"""
        current_code = self._get_current_code()
        task_config = self._get_task_config()
        
        context = CodeReviewContext(
            code=current_code,
            task_id=self.current_task,
            difficulty=task_config['difficulty'],
            description=task_config['description'],
            max_steps=task_config['max_steps'],
            current_step=self.step_count,
            bugs_found=self.bugs_found,
            attempts=len(self.actions_taken)
        )
        
        return Observation(
            code_context=context,
            available_actions=['detect_bug', 'classify_severity', 'suggest_fix', 'explain', 'skip'],
            current_task=self.current_task,
            task_description=task_config['description'],
            step_count=self.step_count,
            max_steps=task_config['max_steps'],
            bugs_found_so_far=len(self.bugs_found),
            total_bugs=len(current_code.known_bugs)
        )