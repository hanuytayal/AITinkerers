import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import json
from datetime import datetime

from services.agent import LogAnalysisAgent
from services.ticket_service import TicketService

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
agent = LogAnalysisAgent()
ticket_service = TicketService()

# Global state to track analysis results
analysis_state = {
    'current_file': None,
    'issues_found': [],
    'tickets_created': [],
    'agent_thoughts': [],
    'reasoning_steps': []
}

@app.route('/')
def index():
    return render_template('index.html', state=analysis_state)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Reset analysis state
        analysis_state['current_file'] = filename
        analysis_state['issues_found'] = []
        analysis_state['tickets_created'] = []
        analysis_state['agent_thoughts'] = []
        analysis_state['reasoning_steps'] = []
        
        return redirect(url_for('analyze', filename=filename))
    
    return redirect(url_for('index'))

@app.route('/analyze/<filename>')
def analyze(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Record agent thought
    analysis_state['agent_thoughts'].append({
        'timestamp': datetime.now().isoformat(),
        'thought': f"Starting analysis of log file: {filename}"
    })
    
    # Read log file
    logs_df = pd.read_csv(filepath)
    
    # Ask the agent to analyze the logs
    issues = agent.analyze_logs(logs_df)
    analysis_state['issues_found'] = issues
    
    # Get reasoning steps from agent
    analysis_state['reasoning_steps'] = agent.get_reasoning_steps()
    
    # Record agent thought
    analysis_state['agent_thoughts'].append({
        'timestamp': datetime.now().isoformat(),
        'thought': f"Found {len(issues)} critical issues in the logs"
    })
    
    # Automatically create tickets for all critical issues
    tickets = []
    if issues:
        analysis_state['agent_thoughts'].append({
            'timestamp': datetime.now().isoformat(),
            'thought': f"Automatically creating tickets for {len(issues)} critical issues"
        })
        
        for issue in issues:
            ticket = ticket_service.create_ticket(issue)
            tickets.append(ticket)
    
    analysis_state['tickets_created'] = tickets
    
    # Record agent thought about tickets created
    if tickets:
        analysis_state['agent_thoughts'].append({
            'timestamp': datetime.now().isoformat(),
            'thought': f"Created {len(tickets)} tickets for oncall engineers"
        })
    
    return render_template('results.html', state=analysis_state)

@app.route('/api/state')
def get_state():
    return jsonify(analysis_state)

@app.route('/api/reasoning')
def get_reasoning():
    """API endpoint to get the latest reasoning steps"""
    return jsonify(analysis_state['reasoning_steps'])

if __name__ == '__main__':
    app.run(debug=True) 