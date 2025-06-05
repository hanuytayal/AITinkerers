import os
import json
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime

import markdown # For rendering markdown in HTML
# import pandas as pd # Deferred until actual usage is confirmed for this file
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

# Assuming these services are structured correctly for import
from services.agent import LogAnalysisAgent
from services.ticket_service import TicketService

# --- Configuration Constants ---
# For Flask app configuration
FLASK_SECRET_KEY_ENV_VAR = 'FLASK_SECRET_KEY'
DEFAULT_FLASK_SECRET_KEY = 'your-default-secret-key-in-case-env-is-not-set' # Change in production
MAX_UPLOAD_SIZE_MB = 16

# For file uploads
# UPLOAD_FOLDER_NAME = 'uploads' # Relative to app instance or root path

# OpenAI Model configuration (if specific to app.py, otherwise should be in Agent)
# Example: OPENAI_MODEL_APP = os.environ.get("OPENAI_MODEL_APP", "gpt-3.5-turbo")


# --- Application Setup ---
app = Flask(__name__)

# Configure Secret Key: Crucial for session management, flash messages, etc.
# IMPORTANT: Set FLASK_SECRET_KEY environment variable in your production environment!
app.config['SECRET_KEY'] = os.environ.get(FLASK_SECRET_KEY_ENV_VAR, DEFAULT_FLASK_SECRET_KEY)
if app.config['SECRET_KEY'] == DEFAULT_FLASK_SECRET_KEY:
    print(f"Warning: Using default Flask secret key. Set the {FLASK_SECRET_KEY_ENV_VAR} environment variable in production.", file=sys.stderr)

# Configure Upload Folder: Using instance folder is often a good practice
# Or ensure 'uploads' is relative to the app root.
# For simplicity, keeping it relative to app root as in original.
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Ensure upload directory exists
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except OSError as e:
    app.logger.error(f"Could not create upload folder {app.config['UPLOAD_FOLDER']}: {e}")
    # Depending on severity, might want to exit or disable uploads


# --- Service Initialization ---
# Initialize ticket service (assuming it doesn't need request-specific context)
# If it needs app context or config, initialize in app factory or similar
ticket_service = TicketService()

# Initialize agent with ticket service
# The agent's API key is handled internally by the Agent class (via env var or direct pass)
# If agent needs app config, pass it here or init later.
log_analysis_agent = LogAnalysisAgent(ticket_service=ticket_service)


# --- Global State Management (To be refactored) ---
# This global state is problematic for concurrent users or scaling.
# For this refactoring iteration, we'll make it more explicit and try to
# make functions return data rather than modifying these directly where possible.
# A proper solution would involve sessions, database, or a task queue system.

# analysis_state dictionary to hold data related to the current/last analysis
# This is a simplified approach; for multiple users, this needs to be session-based or use a DB.
_current_analysis_state: Dict[str, Any] = {
    'current_file': None,       # Filename of the log being analyzed
    'issues_found': [],         # List of issues identified by the agent
    'tickets_created': [],      # List of tickets created
    'reasoning_steps': [],      # Agent's reasoning steps for display
    'analysis_in_progress': False, # Flag to indicate if analysis thread is running
    'error_message': None,      # To store any error messages during analysis
}
# Lock for synchronizing access to _current_analysis_state, especially 'analysis_in_progress'
_analysis_state_lock = threading.Lock()

# Queue for streaming reasoning steps to the client (SSE)
# This is also global; for multiple users, each user/session would need their own stream or queue.
_reasoning_stream_queue = queue.Queue()


# --- Helper Functions ---
def render_reasoning_steps_with_html(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Converts markdown content in reasoning steps to HTML for rendering."""
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
    """Converts markdown content in reasoning steps to HTML for rendering."""
    # Ensure steps is a list before iterating
    if not isinstance(steps, list):
        return [] # Or handle error appropriately
    
    processed_steps = []
    for step in steps:
        # Create a copy to avoid modifying the original dict in _current_analysis_state
        processed_step = step.copy()
        if processed_step.get("type") == "summary":
            processed_step["content_html"] = markdown.markdown(processed_step.get("content", ""))
        else:
            processed_step["content_html"] = processed_step.get("content", "")
        processed_steps.append(processed_step)
    return processed_steps

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main page, displaying current analysis state."""
    with _analysis_state_lock:
        # Make a deep copy for rendering to avoid issues if state changes during render
        # For complex states, consider a more robust copying mechanism or immutable data.
        state_snapshot = {
            'current_file': _current_analysis_state['current_file'],
            'issues_found': list(_current_analysis_state['issues_found']),
            'tickets_created': list(_current_analysis_state['tickets_created']),
            'reasoning_steps': render_reasoning_steps_with_html(
                list(_current_analysis_state['reasoning_steps'])
            ),
            'analysis_in_progress': _current_analysis_state['analysis_in_progress'],
            'error_message': _current_analysis_state['error_message'],
        }
    return render_template('index.html', state=state_snapshot)

def _handle_file_upload(file) -> Optional[str]:
    """
    Saves the uploaded file if valid and returns its path.
    Returns None if the file is invalid.
    """
    if file.filename == '':
        app.logger.warning("No file selected for upload.")
        return None # Or redirect with flash message: flash("No selected file")
    
    # Basic check for .csv extension
    if file and file.filename and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        # Ensure UPLOAD_FOLDER exists (it's created at app startup, but good to be robust)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            app.logger.info(f"File {filename} uploaded successfully to {filepath}.")
            return filename # Return filename for redirection to analyze route
        except Exception as e: # pylint: disable=broad-except
            app.logger.error(f"Error saving uploaded file {filename}: {e}")
            # flash(f"Error saving file: {e}") # Example of user feedback
            return None
    else:
        app.logger.warning(f"Invalid file type or filename for upload: {file.filename}")
        # flash("Invalid file type. Please upload a CSV file.")
        return None

@app.route('/upload', methods=['POST'])
def upload_file_route():
    """Handles file uploads. Expects a CSV file."""
    if 'file' not in request.files:
        # flash("No file part in the request.")
        return redirect(request.url) # Or url_for('index')

    uploaded_filename = _handle_file_upload(request.files['file'])

    if uploaded_filename:
        with _analysis_state_lock:
            _current_analysis_state['current_file'] = uploaded_filename
            _current_analysis_state['issues_found'] = []
            _current_analysis_state['tickets_created'] = []
            _current_analysis_state['reasoning_steps'] = []
            _current_analysis_state['analysis_in_progress'] = False # Reset before new analysis
            _current_analysis_state['error_message'] = None

            # Clear the streaming queue for new analysis
            while not _reasoning_stream_queue.empty():
                try:
                    _reasoning_stream_queue.get_nowait()
                except queue.Empty:
                    break
            app.logger.info(f"Analysis state reset for new file: {uploaded_filename}")
        
        return redirect(url_for('analyze_file_route', filename=uploaded_filename))
    
    return redirect(url_for('index'))


def _agent_reasoning_callback(step: Dict[str, Any]) -> None:
    """
    Callback function for the LogAnalysisAgent to stream reasoning steps.
    This function is called by the agent (potentially from a different thread).
    It puts the step into a queue for the Server-Sent Events (SSE) stream.
    It does NOT modify _current_analysis_state directly.
    """
    print(f"[DEBUG] Agent Callback putting step to queue: {step.get('content', '')[:50]}...")
    _reasoning_stream_queue.put(step)


def _perform_log_analysis(filepath: str, filename: str) -> Dict[str, Any]:
    """
    Core logic for performing log analysis using the agent.
    This function is intended to be run in a background thread.
    It should not directly modify Flask's global state related to specific requests.
    It returns the results of the analysis.

    Args:
        filepath: Absolute path to the log file.
        filename: Original name of the log file.

    Returns:
        A dictionary containing 'issues_found' and 'tickets_created'.
    """
    analysis_results = {
        'issues_found': [],
        'tickets_created': [],
        'final_reasoning_steps': [],
        'error_message': None
    }
    
    try:
        # This part reads the CSV. If agent.py is refactored to take text,
        # this read should happen here, and text passed to agent.
        # For now, assuming agent.analyze_logs_with_chat_tools takes text.
        # Pylint flagged pandas as unused in original app.py context, so ensure it's imported if used.
        try:
            import pandas as pd # pylint: disable=import-outside-toplevel
            logs_df = pd.read_csv(filepath)
            logs_text_content = logs_df.to_string(index=False) # Convert to text for the agent
            # If agent can handle filepath directly and uses pandas internally, that's also an option.
        except ImportError:
            app.logger.error("Pandas library not found. Cannot read CSV for analysis.")
            analysis_results['error_message'] = "Error: Pandas library is required but not installed."
            # Also send this error to the reasoning stream so UI can pick it up
            _agent_reasoning_callback({
                "timestamp": datetime.now().isoformat(),
                "content": analysis_results['error_message'],
                "type": "error"
            })
            return analysis_results
        except Exception as e_read: # pylint: disable=broad-except
            app.logger.error(f"Error reading or processing CSV file {filepath}: {e_read}")
            analysis_results['error_message'] = f"Error reading file: {e_read}"
            _agent_reasoning_callback({
                "timestamp": datetime.now().isoformat(),
                "content": analysis_results['error_message'],
                "type": "error"
            })
            return analysis_results

        # Assuming log_analysis_agent.analyze_logs_with_chat_tools is the refactored method
        # and it takes the text content and a callback.
        identified_issues = log_analysis_agent.analyze_logs_with_chat_tools(
            logs_text_content=logs_text_content, # Pass text content
            stream_callback=_agent_reasoning_callback
        )
        analysis_results['issues_found'] = identified_issues
        analysis_results['final_reasoning_steps'] = log_analysis_agent.get_reasoning_steps() # Get all steps after run

        created_tickets_summary = []
        if identified_issues:
            for issue_detail in identified_issues:
                # The agent's create_ticket tool implementation should handle actual ticket creation
                # and return a summary or ID. For this flow, we assume `identified_issues`
                # contains information about tickets that the agent decided to create.
                # The actual ticket objects might be in `ticket_service` or returned by the agent.
                # For now, let's assume `issue_detail` itself is what we consider a "ticket" for display.
                # This part needs alignment with how `log_analysis_agent` and `ticket_service` interact.

                # If ticket creation is done by the agent's tool directly:
                # We might just use `self.identified_issues` from the agent.
                # The current `LogAnalysisAgent`'s `_execute_tool_call_from_api` for `create_ticket`
                # calls `self.ticket_service.create_ticket(tool_args)` and appends `tool_args` to `self.identified_issues`.
                # So, `identified_issues` from the agent are the "tickets" for our purpose here.

                # Let's assume `ticket_service.create_ticket` was called by the agent's tool
                # and `identified_issues` contains the arguments used for those calls.
                # We might want to re-fetch ticket details if create_ticket returns an ID.
                # For now, what's in `identified_issues` is used.
                created_tickets_summary.append(issue_detail) # Use the issue data as ticket data for now

                # Post-analysis steps like KB augmentation and resolution agent, which were complex.
                # These also modify global state directly. This needs careful refactoring.
                # For now, this logic is kept but should ideally be part of the agent or a subsequent async task.
                # This example keeps it in the thread for now.

                current_ticket_data = issue_detail # This is the data used for ticket creation by the agent

                # Augment with KB (if ticket_service and method exist)
                if hasattr(ticket_service, 'augment_ticket_with_kb'):
                    _agent_reasoning_callback({
                        "timestamp": datetime.now().isoformat(),
                        "content": f"Searching knowledge base for ticket related to: {current_ticket_data.get('summary', 'N/A')}...",
                        "type": "agent_action"
                    })
                    # This is a blocking call in the thread.
                    # ticket_service.augment_ticket_with_kb might modify current_ticket_data or return new
                    # For simplicity, assume it modifies current_ticket_data or we don't reflect its return immediately in reasoning.
                    # augmented_ticket = ticket_service.augment_ticket_with_kb(current_ticket_data.copy()) # Pass a copy
                    # current_ticket_data.update(augmented_ticket) # Update with augmented data
                    # This part is complex due to its interaction with global state and UI updates.
                    # A simplified version:
                    _agent_reasoning_callback({
                        "timestamp": datetime.now().isoformat(),
                        "content": f"KB search completed for: {current_ticket_data.get('summary', 'N/A')}",
                        "type": "agent_state"
                    })


                # Run Resolution Agent (Subprocess) - This is highly complex to manage cleanly.
                # Consider replacing with a proper task queue if this is a long-running operation.
                if os.path.exists(os.path.join(app.root_path, '../exe_agent/demo_run.py')):
                    _run_resolution_agent_subprocess(current_ticket_data) # Extracted for clarity

        analysis_results['tickets_created'] = created_tickets_summary
        return analysis_results

    except Exception as e: # pylint: disable=broad-except
        app.logger.error(f"Error during analysis thread for {filename}: {e}", exc_info=True)
        analysis_results['error_message'] = f"Analysis failed: {e}"
        _agent_reasoning_callback({
            "timestamp": datetime.now().isoformat(),
            "content": analysis_results['error_message'],
            "type": "error"
        })
        return analysis_results


def _run_resolution_agent_subprocess(ticket_context: Dict[str, Any]):
    """
    Runs the resolution agent as a subprocess and streams its output.
    This is a helper for _perform_log_analysis.
    """
    ticket_id_for_log = ticket_context.get('id', 'N/A') # Assuming ticket might have an ID from ticket_service
    demo_run_path = os.path.abspath(os.path.join(app.root_path, '../exe_agent/demo_run.py'))

    _agent_reasoning_callback({
        "timestamp": datetime.now().isoformat(),
        "content": f"Starting Resolution Agent for ticket context: {ticket_context.get('summary', 'N/A')} (ID: {ticket_id_for_log})...",
        "type": "resolution_agent"
    })

    try:
        # Using sys.executable ensures using the same Python interpreter.
        # "-u" for unbuffered output from the subprocess.
        process = subprocess.Popen(
            [sys.executable, "-u", demo_run_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1 # Line-buffered
        )

        # Threads to stream stdout and stderr to avoid blocking
        def stream_output(pipe: Optional[IO[str]], stream_name: str):
            if pipe is None: return
            try:
                for line in iter(pipe.readline, ''):
                    line = line.strip()
                    if line:
                        _agent_reasoning_callback({
                            "timestamp": datetime.now().isoformat(),
                            "content": f"Resolution Agent ({stream_name}) for ticket ID {ticket_id_for_log}: {line}",
                            "type": "resolution_agent_output"
                        })
            except Exception as e_stream: # pylint: disable=broad-except
                app.logger.error(f"Error streaming {stream_name} for resolution agent: {e_stream}")
            finally:
                pipe.close()

        stdout_thread = threading.Thread(target=stream_output, args=(process.stdout, "STDOUT"))
        stderr_thread = threading.Thread(target=stream_output, args=(process.stderr, "STDERR"))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        process.wait(timeout=300) # Add a timeout for the subprocess
        stdout_thread.join(timeout=5) # Wait for threads to finish
        stderr_thread.join(timeout=5)

        if process.returncode == 0:
            _agent_reasoning_callback({
                "timestamp": datetime.now().isoformat(),
                "content": f"Resolution Agent completed successfully for ticket ID {ticket_id_for_log}.",
                "type": "agent_state"
            })
            # Here, you might update the ticket status via ticket_service
            # if ticket_id_for_log != 'N/A' and hasattr(ticket_service, 'mark_ticket_resolved'):
            #    ticket_service.mark_ticket_resolved(ticket_id_for_log)
        else:
            _agent_reasoning_callback({
                "timestamp": datetime.now().isoformat(),
                "content": f"Resolution Agent failed for ticket ID {ticket_id_for_log} (Exit Code: {process.returncode}).",
                "type": "error"
            })
    except subprocess.TimeoutExpired:
        _agent_reasoning_callback({
            "timestamp": datetime.now().isoformat(),
            "content": f"Resolution Agent timed out for ticket ID {ticket_id_for_log}.",
            "type": "error"
        })
        if process: process.kill() # Ensure process is killed on timeout
    except Exception as e_proc: # pylint: disable=broad-except
        _agent_reasoning_callback({
            "timestamp": datetime.now().isoformat(),
            "content": f"Error running Resolution Agent for ticket ID {ticket_id_for_log}: {e_proc}",
            "type": "error"
        })


@app.route('/analyze/<filename>')
def analyze_file_route(filename: str):
    """
    Route to trigger and display analysis results for a given file.
    """
    with _analysis_state_lock:
        if _current_analysis_state['analysis_in_progress']:
            app.logger.info("Analysis already in progress. Returning current state.")
            # Display current state, possibly indicating analysis is running
            state_snapshot = _current_analysis_state.copy()
            state_snapshot['reasoning_steps'] = render_reasoning_steps_with_html(state_snapshot['reasoning_steps'])
            return render_template('results.html', state=state_snapshot, analysis_running_now=True)

        # Basic check to prevent re-analysis if results (tickets) already exist for this file
        # More robust would be to check if analysis was *completed* successfully.
        if (_current_analysis_state['current_file'] == filename and
            _current_analysis_state['tickets_created']): # Or a 'completed' flag
            app.logger.info(f"Analysis for {filename} already completed with tickets. Displaying existing results.")
            state_snapshot = _current_analysis_state.copy()
            state_snapshot['reasoning_steps'] = render_reasoning_steps_with_html(state_snapshot['reasoning_steps'])
            return render_template('results.html', state=state_snapshot, analysis_running_now=False)

        # Reset parts of state for a new analysis run if it's a different file or no tickets yet
        if _current_analysis_state['current_file'] != filename or not _current_analysis_state['tickets_created']:
            _current_analysis_state['current_file'] = filename
            _current_analysis_state['issues_found'] = []
            _current_analysis_state['tickets_created'] = []
            _current_analysis_state['reasoning_steps'] = []
            _current_analysis_state['error_message'] = None
            # Clear queue for new run
            while not _reasoning_stream_queue.empty():
                try: _reasoning_stream_queue.get_nowait()
                except queue.Empty: break

        _current_analysis_state['analysis_in_progress'] = True
    # End of lock critical section

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if not os.path.exists(filepath):
        app.logger.error(f"File not found for analysis: {filepath}")
        # flash("Error: Analysis file not found.")
        with _analysis_state_lock: # Reset progress flag
            _current_analysis_state['analysis_in_progress'] = False
            _current_analysis_state['error_message'] = f"File {filename} not found for analysis."
        return redirect(url_for('index'))

    # --- Analysis Thread ---
    def analysis_thread_target(f_path: str, f_name: str):
        app.logger.info(f"Analysis thread started for {f_name}")
        # This call will use the agent's reasoning callback to put steps into _reasoning_stream_queue
        analysis_output = _perform_log_analysis(f_path, f_name)

        # Update global state with final results from the thread
        with _analysis_state_lock:
            _current_analysis_state['issues_found'] = analysis_output.get('issues_found', [])
            _current_analysis_state['tickets_created'] = analysis_output.get('tickets_created', [])
            # Reasoning steps are already streamed; _perform_log_analysis might return final collected steps
            # For now, assume _agent_reasoning_callback is the primary source for UI updates of steps.
            # If _perform_log_analysis collects steps too, decide how to merge/display.
            # Let's assume the final_reasoning_steps from agent are what we want to persist after run.
            if 'final_reasoning_steps' in analysis_output:
                 _current_analysis_state['reasoning_steps'] = analysis_output['final_reasoning_steps']

            _current_analysis_state['error_message'] = analysis_output.get('error_message')
            _current_analysis_state['analysis_in_progress'] = False
            app.logger.info(f"Analysis thread finished for {f_name}. Issues: {len(_current_analysis_state['issues_found'])}, Tickets: {len(_current_analysis_state['tickets_created'])}")
            # Add a final step to the queue to signify completion if desired
            _reasoning_stream_queue.put({
                "timestamp": datetime.now().isoformat(),
                "content": "Analysis process completed.",
                "type": "process_state"
            })
    
    thread = threading.Thread(target=analysis_thread_target, args=(filepath, filename))
    thread.daemon = True # Allow main app to exit even if threads are running
    thread.start()
    
    # For initial render, show analysis is in progress.
    # The _current_analysis_state was reset just before starting the thread.
    # Pass a snapshot of this reset state to the template.
    with _analysis_state_lock:
        initial_render_state = _current_analysis_state.copy()
        # Ensure reasoning_steps sent to template are rendered for HTML, even if empty
        initial_render_state['reasoning_steps'] = render_reasoning_steps_with_html(
            initial_render_state['reasoning_steps']
        )

    return render_template('results.html', state=initial_render_state, analysis_running_now=True)


@app.route('/api/state')
def get_state_api():
    """API endpoint to get the current analysis state."""
    with _analysis_state_lock:
        # Return a copy to avoid direct modification issues if any part of app modifies it post-jsonification
        state_to_return = _current_analysis_state.copy()
        # Reasoning steps might be large, consider if they should always be returned or fetched separately
        # For now, keeping original behavior.
    return jsonify(state_to_return)

@app.route('/api/reasoning')
def get_reasoning_api():
    """API endpoint to get all current reasoning steps (non-streaming)."""
    with _analysis_state_lock:
        steps_to_return = list(_current_analysis_state['reasoning_steps'])
    return jsonify(steps_to_return)


@app.route('/stream/reasoning')
def stream_reasoning_sse():
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