# Architecture: Automated Troubleshooting Demo

## System Overview
This project automates system and database troubleshooting using a Python Selenium agent, a structured runbook, a React-based frontend for on-call task management, and a Flask-based log analyzer for diagnostics and ticketing. The components can be used independently or as an integrated workflow.

## Components
- **Runbook (`exe_agent/demo_runbook.txt`)**
  - Human-readable, stepwise instructions for troubleshooting
  - Only robust, reliable actions (web and CLI)
- **Agent (`exe_agent/browser_use_agent.py`)**
  - Parses and executes runbook actions
  - Manages browser (Selenium) and CLI subprocesses
  - Handles screenshots, text extraction, and resource cleanup
- **Demo Runner (`exe_agent/demo_run.py`)**
  - Loads the runbook and invokes the agent for demonstration
- **Frontend (`frontend/on-call/`)**
  - React app for on-call/incident management
  - Kanban board, task tracking, and UI for incident response
  - Integrates with backend for live updates and ticketing
- **Log Analyzer (`logs_analyzer/`)**
  - Flask backend for log ingestion, analysis, and ticketing
  - Supports uploading logs, running playbooks, and generating diagnostic reports
  - REST API for integration with frontend or agent
- **Screenshots & Results**
  - Screenshots saved in `exe_agent/screenshots/` or `diagnostic_results/`
  - Diagnostic text in `investigation_results.txt`

## Workflow Diagram
```
[Runbook] --> [Agent] --> [Web/CLI Actions] --> [Collect Results] --> [Export/Save]
                                             |
                                             v
                                [Log Analyzer Backend]
                                             |
                                             v
                                 [Frontend On-Call UI]
```

## Example Use Cases
- Automated system/database diagnostics via agent and runbook
- Log upload, analysis, and ticketing via Flask backend
- On-call task management and incident tracking via React frontend
- Integrated workflow: agent results and log analysis surfaced in frontend

## Design Decisions
- **No fragile selectors or unreliable web tasks**
- **No unused YAML or legacy logic**
- **All actions are resource-safe and repeatable**
- **Frontend and backend are modular and can be extended**

## Extensibility
- Add new runbook or playbook steps for diagnostics
- Integrate agent with backend/frontend for live troubleshooting
- Enhance log analysis, ticketing, and UI features

---
See `README.md` for usage instructions.
