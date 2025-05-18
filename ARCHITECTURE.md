# AITinkerers-3 Architecture

## High-Level Overview

AITinkerers-3 is a modular automation and troubleshooting platform with three main subsystems:

- **exe_agent/**: Python-based agent for browser, CLI, and API automation
- **frontend/**: React web UI for on-call and task management
- **logs_analyzer/**: Python service for log analysis and ticketing

These components interact via files, APIs, and shared data to provide a seamless troubleshooting and automation experience.

---

## Component Details

### 1. exe_agent (Automation Agent)
- **Purpose:** Automates browser actions, CLI commands, and API calls using runbooks.
- **Key Modules:**
  - `browser_use_agent.py`: Core agent for browser/CLI/API actions (Selenium-based)
  - `demo_runbook.txt`: Example runbook for troubleshooting
  - `demo_run.py`: Script to execute a runbook
- **Capabilities:**
  - Opens browser windows, navigates, searches, extracts data
  - Executes CLI commands in new macOS Terminal windows
  - Makes API calls and parses results
  - Takes screenshots and saves diagnostic artifacts
  - Follows step-by-step runbooks for repeatable troubleshooting

### 2. frontend (React UI)
- **Purpose:** Provides a web interface for on-call engineers and task management
- **Key Modules:**
  - `src/`: React components for board, columns, tasks, etc.
  - `public/`: Static assets
- **Capabilities:**
  - Kanban-style task board
  - Task detail modals and status tracking
  - Integration with backend services (future)

### 3. logs_analyzer (Log Analysis & Ticketing)
- **Purpose:** Analyzes logs, generates reports, and manages tickets
- **Key Modules:**
  - `app.py`, `run.py`: Main app and runner
  - `services/`: Ticketing and file utilities
  - `static/`, `templates/`: Web UI for log analysis
- **Capabilities:**
  - Ingests and analyzes logs
  - Generates diagnostic reports
  - Provides a web UI for results and ticket management

---

## Data Flow

1. **Runbook Execution:**
   - User triggers a runbook via `demo_run.py`
   - `browser_use_agent.py` executes each step (browser, CLI, API)
   - Results (screenshots, logs) are saved to disk

2. **Frontend Interaction:**
   - Users interact with the React UI for task management
   - (Future) UI may trigger backend automation or display results

3. **Log Analysis:**
   - Logs are uploaded to `logs_analyzer`
   - Reports and tickets are generated and displayed in the web UI

---

## Extensibility
- Add new runbooks to `exe_agent/` for different troubleshooting scenarios
- Extend the agent to support more actions (file ops, notifications, etc.)
- Integrate frontend with backend APIs for real-time updates
- Add new log parsers or ticketing integrations in `logs_analyzer/`

---

## Technology Stack
- **Python 3.11+** (backend, agent, log analysis)
- **Selenium** (browser automation)
- **React** (frontend)
- **Node.js** (frontend tooling)
- **macOS** (for Terminal integration)

---

## Example Workflow
1. Engineer runs a database troubleshooting runbook
2. Agent checks system and database status, collects logs, takes screenshots
3. Results are saved and can be reviewed or uploaded to the logs analyzer
4. On-call engineers track and resolve issues via the frontend UI

---

For more details, see the code in each subdirectory and the main [README.md](README.md).
