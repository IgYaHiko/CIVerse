"""
Flask API Routes
REST endpoints for React frontend
"""

from flask import Blueprint, request, jsonify
from environment import CodeReviewEnvironment, Action

# Create blueprint
api = Blueprint('api', __name__)

# Initialize environment
env = CodeReviewEnvironment()

@api.route('/reset', methods=['GET', 'POST'])
def reset():
    """Reset environment and return initial observation"""
    try:
        observation = env.reset()
        
        return jsonify({
            'success': True,
            'observation': {
                'task_id': observation.current_task,
                'task_description': observation.task_description,
                'code': observation.code_context.code.code,
                'filename': observation.code_context.code.filename,
                'step_count': observation.step_count,
                'max_steps': observation.max_steps,
                'bugs_found_so_far': observation.bugs_found_so_far,
                'total_bugs': observation.total_bugs
            },
            'available_actions': observation.available_actions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/step', methods=['POST'])
def step():
    """Execute an action and return result"""
    try:
        data = request.json
        action = Action(**data)
        
        observation, reward, done, info = env.step(action)
        
        return jsonify({
            'success': True,
            'observation': {
                'task_id': observation.current_task,
                'task_description': observation.task_description,
                'code': observation.code_context.code.code,
                'filename': observation.code_context.code.filename,
                'step_count': observation.step_count,
                'max_steps': observation.max_steps,
                'bugs_found_so_far': observation.bugs_found_so_far,
                'total_bugs': observation.total_bugs
            },
            'reward': {
                'score': reward.score,
                'feedback': reward.feedback,
                'breakdown': reward.breakdown
            },
            'done': done,
            'info': info,
            'total_score': env.total_score
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/state', methods=['GET'])
def get_state():
    """Get current environment state"""
    try:
        state = env.state()
        
        return jsonify({
            'success': True,
            'state': {
                'current_task': state.current_task,
                'step_count': state.step_count,
                'total_score': state.total_score,
                'tasks_completed': state.tasks_completed,
                'bugs_found': [bug.dict() for bug in state.bugs_found],
                'actions_taken': [action.dict() for action in state.actions_taken]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'environment': 'code-review-assistant'})