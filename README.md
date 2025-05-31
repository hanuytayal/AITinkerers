# Project: Automated System & Database Troubleshooting Demo

## Overview
This project demonstrates an automated troubleshooting workflow for system and database issues using a Python Selenium agent, a robust runbook, a React-based frontend for on-call task management, and a Flask-based log analyzer for deeper diagnostics. The system executes both web and CLI actions, collects diagnostics, and provides a user-friendly interface for rapid incident response.

## Key Components
- **Runbook (`exe_agent/demo_runbook.txt`)**: Defines a reliable sequence of troubleshooting steps, including:
  - Checking GitHub status (web)
  - Checking disk space (CLI)
  - Checking Docker/Postgres status and logs (CLI)
  - Exporting results and screenshots
- **Agent (`exe_agent/browser_use_agent.py`)**: Executes runbook actions, manages browser and CLI tasks, and handles resource cleanup.
- **Demo Runner (`exe_agent/demo_run.py`)**: Runs the agent with the runbook for demonstration.
- **Frontend (`frontend/on-call/`)**: React app for on-call task management, Kanban board, and incident tracking. Integrates with backend for live updates.
- **Log Analyzer (`logs_analyzer/`)**: Flask app for log ingestion, analysis, and ticketing. Supports uploading logs, running playbooks, and generating diagnostic reports.
- **Screenshots & Results**: Diagnostic screenshots and result files are saved in `exe_agent/screenshots/` and `diagnostic_results/`.

## How to Run the Demo
1. **Install agent dependencies:**
   ```sh
   cd exe_agent && pip install -r requirements.txt
   ```
2. **Run the agent demo:**
   ```sh
   cd exe_agent && python demo_run.py
   ```
3. **Run the log analyzer backend:**
   ```sh
   cd logs_analyzer && pip install -r requirements.txt && python run.py
   ```
4. **Run the frontend (on-call dashboard):**
   ```sh
   cd frontend/on-call && npm install && npm start
   ```
5. **Review results:**
   - Screenshots: `exe_agent/screenshots/` or `diagnostic_results/`
   - Diagnostic text: `investigation_results.txt`
   - Log analysis: `logs_analyzer/` web UI
   - On-call board: `frontend/on-call/` web UI

## Design Principles
- **Reliability:** Only robust, repeatable actions are included in the runbook.
- **Simplicity:** The workflow is concise and easy to extend.
- **Documentation:** All steps and architecture are documented for clarity.
- **Separation of Concerns:** Agent, frontend, and log analyzer are modular and can be used independently or together.

## Project Structure
- `exe_agent/` — Agent logic, runbook, and demo runner
- `frontend/on-call/` — React frontend for on-call/incident management
- `logs_analyzer/` — Flask backend for log analysis and ticketing
- `README.md` — Project overview and instructions
- `ARCHITECTURE.md` — System architecture and workflow

## Further Improvements
- Add advanced error handling
- Expand runbook and playbook scenarios
- Integrate agent with frontend/backend for live troubleshooting
- Enhance log analysis and ticketing automation

---
For architecture details, see `ARCHITECTURE.md`.