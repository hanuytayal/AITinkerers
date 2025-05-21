import os
import shutil
import pandas as pd
from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Adjust import paths for service classes
from .log_analyzer_services.agent import LogAnalysisAgent
from .log_analyzer_services.ticket_service import TicketService
from .log_analyzer_services.file_utils import save_uploaded_file # Assuming this is the correct function

router = APIRouter()

# Ensure the uploads directory exists
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Simple in-memory storage for results (for inspection)
analysis_results_store: Dict[str, Any] = {}

class LogAnalysisResponse(BaseModel):
    message: str
    filename: str
    analysis_id: str # To retrieve results later

class AnalysisResult(BaseModel):
    status: str
    issues_found: List[Dict]
    tickets_created: List[Dict] # Assuming tickets are dicts for now
    reasoning_steps: List[Dict]


def run_log_analysis(filepath: str, filename: str, analysis_id: str):
    """
    Background task to run log analysis.
    """
    print(f"Background task started for {filename} (ID: {analysis_id})")
    analysis_results_store[analysis_id] = {"status": "processing", "issues_found": [], "tickets_created": [], "reasoning_steps": []}
    try:
        # 1. Read the CSV file using pandas
        try:
            df = pd.read_csv(filepath)
            print(f"Successfully read CSV: {filepath}")
        except Exception as e:
            print(f"Error reading CSV {filepath}: {e}")
            analysis_results_store[analysis_id]["status"] = "failed_reading_csv"
            analysis_results_store[analysis_id]["error"] = str(e)
            raise HTTPException(status_code=500, detail=f"Error reading CSV: {e}")

        # 2. Instantiate LogAnalysisAgent and TicketService
        # OPENAI_API_KEY should be set as an environment variable
        # Ensure TicketService is initialized correctly (e.g. with KB if needed)
        ticket_service = TicketService()
        log_agent = LogAnalysisAgent(ticket_service=ticket_service)
        print("LogAnalysisAgent and TicketService instantiated.")

        # Define a callback for streaming reasoning steps
        def reasoning_stream_callback(step_data):
            print(f"Reasoning step received for {analysis_id}: {step_data}")
            if analysis_id in analysis_results_store:
                 analysis_results_store[analysis_id]["reasoning_steps"].append(step_data)

        # 3. Run analysis
        print(f"Starting log analysis for {filename}...")
        issues_found = log_agent.analyze_logs(df, stream_callback=reasoning_stream_callback)
        print(f"Log analysis completed for {filename}. Issues found: {len(issues_found)}")

        analysis_results_store[analysis_id]["issues_found"] = issues_found
        analysis_results_store[analysis_id]["reasoning_steps"] = log_agent.get_reasoning_steps() # Get all steps after analysis

        # 4. Create tickets for identified issues (simplified)
        created_tickets = []
        if ticket_service:
            for issue in issues_found:
                # The agent now directly returns issue details suitable for ticket creation
                # but we might need to adapt if the format is not direct
                ticket = ticket_service.create_ticket(issue)
                # Augment with KB
                ticket_service.augment_ticket_with_kb(ticket)
                created_tickets.append(ticket)
            print(f"Tickets created for {filename}: {len(created_tickets)}")
            analysis_results_store[analysis_id]["tickets_created"] = created_tickets
        
        analysis_results_store[analysis_id]["status"] = "completed"
        print(f"Background task finished for {filename} (ID: {analysis_id})")

    except Exception as e:
        print(f"Error during log analysis for {filename} (ID: {analysis_id}): {e}")
        analysis_results_store[analysis_id]["status"] = "failed_analysis"
        analysis_results_store[analysis_id]["error"] = str(e)
    finally:
        # Optional: Clean up the uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Cleaned up uploaded file: {filepath}")


@router.post("/analyze_log", response_model=LogAnalysisResponse)
async def analyze_log_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    # Generate a unique ID for this analysis
    analysis_id = f"analysis_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S%f')}"

    try:
        # Save the uploaded file to the UPLOADS_DIR
        # The save_uploaded_file function from file_utils.py should handle this.
        # If it's not structured to return the full path, we adjust.
        # For now, let's assume it saves and returns the path.
        
        # Path where the file will be saved
        filepath = os.path.join(UPLOADS_DIR, file.filename)
        
        # Save the file using shutil or a utility function
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # If you had a specific save_uploaded_file function:
        # filepath = save_uploaded_file(file, UPLOADS_DIR) # This was the original intent

        print(f"File {file.filename} saved to {filepath}")

    except Exception as e:
        print(f"Error saving file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {e}")

    # Add the analysis task to background
    background_tasks.add_task(run_log_analysis, filepath, file.filename, analysis_id)
    print(f"Log analysis task for {file.filename} (ID: {analysis_id}) added to background.")

    return {
        "message": "Log analysis started in background", 
        "filename": file.filename,
        "analysis_id": analysis_id
    }

# Endpoint to get results (for inspection)
@router.get("/analyze_log/results/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_results(analysis_id: str):
    result = analysis_results_store.get(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    if result["status"] == "processing":
        raise HTTPException(status_code=202, detail="Analysis still processing.") # Accepted
    if "error" in result: # If failed
        raise HTTPException(status_code=500, detail=f"Analysis failed: {result.get('error', 'Unknown error')}")
    return result

# Health check or root for the router
@router.get("/log_analyzer_health")
async def health_check():
    return {"status": "Log Analyzer router is running"}
