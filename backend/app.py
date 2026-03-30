"""
Flask Application Entry Point
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import from api_routes
from api_routes import api

# Create Flask app
app = Flask(__name__)

# Enable CORS for React frontend
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001', 'http://localhost:5173'])

# Register blueprints
app.register_blueprint(api, url_prefix='/api')

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'name': 'Code Review Assistant',
        'version': '1.0.0',
        'description': 'OpenEnv for AI agents to learn code review',
        'endpoints': {
            'reset': 'POST /api/reset - Reset environment',
            'step': 'POST /api/step - Execute action',
            'state': 'GET /api/state - Get current state',
            'health': 'GET /api/health - Health check'
        },
        'tasks': [
            {'id': 1, 'name': 'Bug Detection', 'difficulty': 'easy'},
            {'id': 2, 'name': 'Bug Classification', 'difficulty': 'medium'},
            {'id': 3, 'name': 'Fix Suggestion', 'difficulty': 'hard'}
        ]
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 7860))
    app.run(host='0.0.0.0', port=port, debug=True)