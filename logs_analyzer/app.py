import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from werkzeug.utils import secure_filename
import pandas as pd
import json
from datetime import datetime
import queue
import threading
import markdown
import subprocess
import sys
import time

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
                    # Create the ticket first
                    ticket = ticket_service.create_ticket(issue)
                    # Add ticket to the tickets list immediately
                    tickets.append(ticket)
                    # Add a step indicating ticket creation
                    ticket_created_step = {
                        "timestamp": datetime.now().isoformat(),
                        "content": f"Ticket {ticket['id']} created with status: {ticket['status']}",
                        "type": "agent_state"
                    }
                    analysis_state['reasoning_steps'].append(ticket_created_step)
                    reasoning_stream.put(ticket_created_step)
                    print(f"[DEBUG] Ticket {ticket['id']} created")
                    
                    # Update the global state immediately after ticket creation
                    analysis_state['tickets_created'] = tickets
                    
                    # Process knowledge base information separately
                    try:
                        if "knowledge_base" in ticket and ticket["knowledge_base"]:
                            kb_entries = ticket["knowledge_base"]
                            kb_titles = [entry.get("title", "Untitled") for entry in kb_entries]
                            kb_links = [entry.get("link", "") for entry in kb_entries]
                            # Create a more detailed message
                            kb_reasoning = f"Knowledge Base Agent found {len(kb_entries)} relevant document(s) for ticket {ticket['id']}:"
                            for i, (title, link) in enumerate(zip(kb_titles, kb_links)):
                                kb_reasoning += f"\n- {title} ({link})"
                            kb_step = {
                                "timestamp": datetime.now().isoformat(),
                                "content": kb_reasoning,
                                "type": "agent_state"
                            }
                            analysis_state['reasoning_steps'].append(kb_step)
                            reasoning_stream.put(kb_step)
                            print(f"[DEBUG] Added KB step for ticket {ticket['id']}")
                            
                            # Add a step indicating KB augmentation
                            kb_update_step = {
                                "timestamp": datetime.now().isoformat(),
                                "content": f"Ticket {ticket['id']} augmented with Knowledge Base references",
                                "type": "agent_state"
                            }
                            analysis_state['reasoning_steps'].append(kb_update_step)
                            reasoning_stream.put(kb_update_step)
                            # Let the UI update before proceeding
                            time.sleep(0.5)

                        # --- Run the resolution agent as a subprocess (streamed) ---
                        demo_run_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../exe_agent/demo_run.py'))
                        
                        # Indicate resolution agent is starting
                        start_resolution_step = {
                            "timestamp": datetime.now().isoformat(),
                            "content": f"Starting Resolution Agent for ticket {ticket['id']}...",
                            "type": "resolution_agent"
                        }
                        analysis_state['reasoning_steps'].append(start_resolution_step)
                        reasoning_stream.put(start_resolution_step)
                        print(f"[DEBUG] Starting Resolution Agent for ticket {ticket['id']}")
                        
                        # Ensure we flush all pending steps before starting subprocess
                        sys.stdout.flush()
                        time.sleep(1.0)  # Give UI time to update
                        
                        # Use non-blocking queue for collecting output
                        stdout_queue = queue.Queue()
                        stderr_queue = queue.Queue()
                        
                        # Use unbuffered pipe to ensure immediate output
                        process = subprocess.Popen(
                            [sys.executable, "-u", demo_run_path],  # -u for unbuffered output
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            bufsize=0  # Unbuffered
                        )
                        
                        # Stream stdout and stderr in real time with immediate flushing
                        def stream_subprocess_output(stream, stream_type, output_queue):
                            try:
                                line_counter = 0
                                for line in iter(stream.readline, ''):
                                    if not line:
                                        break
                                    
                                    line_counter += 1
                                    line = line.strip()
                                    if line:
                                        print(f"[DEBUG] {stream_type} line {line_counter}: {line}")
                                        # Store in queue for later processing
                                        output_queue.put(line)
                                        
                                        # Send to reasoning stream
                                        resolution_step = {
                                            "timestamp": datetime.now().isoformat(),
                                            "content": f"Resolution Agent {stream_type} for ticket {ticket['id']}: {line}",
                                            "type": "resolution_agent"
                                        }
                                        analysis_state['reasoning_steps'].append(resolution_step)
                                        reasoning_stream.put(resolution_step)
                                        
                                        # Flush to ensure immediate delivery
                                        sys.stdout.flush()
                                        
                                print(f"[DEBUG] {stream_type} stream complete after {line_counter} lines")
                            except Exception as e:
                                print(f"[ERROR] Exception in {stream_type} stream thread: {e}")
                                import traceback
                                traceback.print_exc()
                            finally:
                                stream.close()
                        
                        # Run stream readers in separate threads
                        stdout_thread = threading.Thread(
                            target=stream_subprocess_output, 
                            args=(process.stdout, 'STDOUT', stdout_queue)
                        )
                        stderr_thread = threading.Thread(
                            target=stream_subprocess_output, 
                            args=(process.stderr, 'STDERR', stderr_queue)
                        )
                        
                        stdout_thread.daemon = True
                        stderr_thread.daemon = True
                        stdout_thread.start()
                        stderr_thread.start()
                        
                        print(f"[DEBUG] Waiting for process to complete...")
                        
                        # Wait for the subprocess to complete
                        process.wait()
                        
                        print(f"[DEBUG] Process completed with return code {process.returncode}")
                        
                        # Wait for the threads to finish reading output
                        stdout_thread.join(timeout=3.0)
                        stderr_thread.join(timeout=3.0)
                        
                        # Process any remaining output in the queues
                        stdout_lines = []
                        while not stdout_queue.empty():
                            stdout_lines.append(stdout_queue.get())
                        
                        stderr_lines = []
                        while not stderr_queue.empty():
                            stderr_lines.append(stderr_queue.get())
                            
                        print(f"[DEBUG] Total output captured: {len(stdout_lines)} stdout lines, {len(stderr_lines)} stderr lines")
                        
                        resolution_log_content = "STDOUT:\n" + "\n".join(stdout_lines) + "\n\nSTDERR:\n" + "\n".join(stderr_lines)

                        # Ensure we flush all pending steps before marking as resolved
                        time.sleep(1.0)  # Give previous steps time to be sent to client
                        
                        # After process successfully completes, mark ticket as resolved
                        if process.returncode == 0:
                            ticket_service.mark_ticket_resolved(ticket['id'])
                            
                            # Update the ticket in the analysis_state
                            for i, t in enumerate(analysis_state['tickets_created']):
                                if t['id'] == ticket['id']:
                                    analysis_state['tickets_created'][i]['status'] = "Resolved"
                                    analysis_state['tickets_created'][i]['resolution_log'] = resolution_log_content
                                    break
                                    
                            # Create a completion step
                            resolved_step = {
                                "timestamp": datetime.now().isoformat(),
                                "content": f"Ticket {ticket['id']} has been resolved by the Resolution Agent.",
                                "type": "agent_state"
                            }
                            analysis_state['reasoning_steps'].append(resolved_step)
                            reasoning_stream.put(resolved_step)
                            
                            # Append to the ticket
                            ticket_service.append_to_ticket(
                                ticket['id'], 
                                f"Ticket {ticket['id']} resolved by Resolution Agent. Full log available in ticket details."
                            )
                            print(f"[DEBUG] Resolution agent completed and ticket {ticket['id']} marked as resolved")
                        else:
                            error_step = {
                                "timestamp": datetime.now().isoformat(),
                                "content": f"Resolution Agent failed for ticket {ticket['id']} with exit code {process.returncode}",
                                "type": "error"
                            }
                            analysis_state['reasoning_steps'].append(error_step)
                            reasoning_stream.put(error_step)
                            print(f"[ERROR] Resolution agent failed with exit code {process.returncode}")

                    except Exception as e:
                        print(f"[ERROR] Knowledge base or resolution agent processing error: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Update the global state with all tickets
                analysis_state['tickets_created'] = tickets
                print(f"[DEBUG] Added {len(tickets)} tickets to analysis_state")
            
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
                # Force flush after each event
                yield f": keepalive\n\n"
        
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
                    # Force flush after each event
                    yield f": keepalive\n\n"
            except queue.Empty:
                # Send a heartbeat to keep the connection alive
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
                # Force flush
                yield f": keepalive\n\n"
    
    return Response(event_stream(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True) 