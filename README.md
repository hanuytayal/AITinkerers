# AITinkerers-3

## Overview

AITinkerers-3 is a multi-component automation and troubleshooting platform designed for system diagnostics, browser automation, and developer productivity. It combines browser-based automation, CLI command execution, API calls, and runbook-driven workflows to help engineers investigate and resolve issues efficiently.

## Main Components

- **exe_agent/**: Python agent for browser automation, CLI, and API actions using Selenium. Executes runbooks for troubleshooting and diagnostics.
- **frontend/**: React-based web UI for on-call and task management.
- **logs_analyzer/**: Python service for log analysis, ticketing, and reporting.
- **data/**: Stores logs and playbooks for troubleshooting.

## Key Features
- Automated browser navigation and data extraction
- CLI command execution (with macOS Terminal integration)
- API calls and result parsing
- Screenshot capture and result documentation
- Runbook-driven, step-by-step troubleshooting
- Modular architecture for easy extension

## Quickstart

1. **Install dependencies**
   ```sh
   cd exe_agent
   pip install -r requirements.txt
   ```

2. **Run a demo troubleshooting runbook**
   ```sh
   python demo_run.py
   ```

3. **View results**
   - Screenshots: `exe_agent/screenshots/`
   - Diagnostic files: `exe_agent/`

4. **Frontend**
   ```sh
   cd frontend
   npm install
   npm start
   ```

5. **Logs Analyzer**
   ```sh
   cd logs_analyzer
   pip install -r requirements.txt
   python run.py
   ```

## Folder Structure

- `exe_agent/` - Browser/CLI agent and runbooks
- `frontend/` - React web UI
- `logs_analyzer/` - Log analysis and ticketing
- `data/` - Logs and playbooks

## Requirements
- Python 3.11+
- Node.js (for frontend)
- Google Chrome or Chromium (for browser automation)
- macOS (for Terminal integration)

## Contributing
Pull requests and issues are welcome!

---

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed overview of the system design.