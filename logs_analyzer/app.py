import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from werkzeug.utils import secure_filename
import pandas as pd
import json
from datetime import datetime
import queue
import threading
import markdown

from services.agent import LogAnalysisAgent
from services.ticket_service import TicketService

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize ticket service
ticket_service = TicketService()

# Initialize agent with ticket service
agent = LogAnalysisAgent(ticket_service=ticket_service)

# Global state to track analysis results
analysis_state = {
    'current_file': None,
    'issues_found': [],
    'tickets_created': [],
    'reasoning_steps': []
}

# Queue for streaming reasoning steps
reasoning_stream = queue.Queue()

# Flag to track if analysis is running
analysis_running = False

def render_reasoning_steps_with_html(steps):
    for step in steps:
        if step.get("type") == "summary":
            step["content_html"] = markdown.markdown(step["content"])
        else:
            step["content_html"] = step["content"]
    return steps

@app.route('/')
def index():
    state = analysis_state.copy()
    state['reasoning_steps'] = render_reasoning_steps_with_html(state['reasoning_steps'])
    return render_template('index.html', state=state)

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
        analysis_state['reasoning_steps'] = []
        
        # Clear the streaming queue
        while not reasoning_stream.empty():
            reasoning_stream.get()
        
        return redirect(url_for('analyze', filename=filename))
    
    return redirect(url_for('index'))

def reasoning_callback(step):
    print(f"[DEBUG] reasoning_callback called: {step}")
    """Callback function for streaming reasoning steps"""
    # Check if this step already exists (using content and timestamp as identifiers)
    step_already_exists = False
    for existing_step in analysis_state['reasoning_steps']:
        if (existing_step.get('content') == step.get('content') and 
            existing_step.get('timestamp') == step.get('timestamp')):
            step_already_exists = True
            break
    
    # Only add if not a duplicate
    if not step_already_exists:
        # Add the step to the global state
        analysis_state['reasoning_steps'].append(step)
        # Add to streaming queue
        reasoning_stream.put(step)

@app.route('/analyze/<filename>')
def analyze(filename):
    global analysis_running
    
    # Prevent multiple analyses running at the same time
    if analysis_running:
        state = analysis_state.copy()
        state['reasoning_steps'] = render_reasoning_steps_with_html(state['reasoning_steps'])
        return render_template('results.html', state=state)

    # Prevent re-running analysis if tickets already exist for this file
    if (analysis_state['current_file'] == filename and analysis_state['tickets_created']):
        state = analysis_state.copy()
        state['reasoning_steps'] = render_reasoning_steps_with_html(state['reasoning_steps'])
        return render_template('results.html', state=state)

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Read log file
    logs_df = pd.read_csv(filepath)
    
    # Start a thread to run the analysis so it doesn't block the response
    def run_analysis():
        global analysis_running
        print("[DEBUG] run_analysis started")
        analysis_running = True
        try:
            # Ask the agent to analyze the logs with streaming callback
            agent.analyze_logs(logs_df, stream_callback=reasoning_callback)
            # Always get the final issues from the agent after analysis
            final_issues = agent.get_identified_issues()
            analysis_state['issues_found'] = final_issues

            tickets = []
            if final_issues:
                for issue in final_issues:
                    ticket = ticket_service.create_ticket(issue)
                    tickets.append(ticket)
            analysis_state['tickets_created'] = tickets
            print("[DEBUG] run_analysis completed")
        finally:
            analysis_running = False
    
    # Start the analysis in a background thread
    threading.Thread(target=run_analysis).start()
    
    state = analysis_state.copy()
    state['reasoning_steps'] = render_reasoning_steps_with_html(state['reasoning_steps'])
    return render_template('results.html', state=state)

@app.route('/api/state')
def get_state():
    return jsonify(analysis_state)

@app.route('/api/reasoning')
def get_reasoning():
    """API endpoint to get the latest reasoning steps"""
    return jsonify(analysis_state['reasoning_steps'])

@app.route('/stream/reasoning')
def stream_reasoning():
    """Server-sent events (SSE) endpoint for streaming reasoning steps in real-time"""
    def event_stream():
        # Keep track of sent steps to avoid duplicates
        sent_steps = set()
        
        # First send all existing steps
        for i, step in enumerate(analysis_state['reasoning_steps']):
            # Create a unique identifier for the step
            step_id = f"{step.get('timestamp')}-{step.get('content')[:30]}"
            if step_id not in sent_steps:
                sent_steps.add(step_id)
                yield f"data: {json.dumps(step)}\n\n"
        
        # Then stream new steps as they come in
        while True:
            try:
                # Get the next step with a timeout
                step = reasoning_stream.get(timeout=1.0)
                
                # Create a unique identifier for the step
                step_id = f"{step.get('timestamp')}-{step.get('content')[:30]}"
                
                # Only send if not already sent
                if step_id not in sent_steps:
                    sent_steps.add(step_id)
                    yield f"data: {json.dumps(step)}\n\n"
            except queue.Empty:
                # Send a heartbeat to keep the connection alive
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
    
    return Response(event_stream(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True) 