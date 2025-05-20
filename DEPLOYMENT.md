# Deployment Guide

This document provides a high-level overview of how to deploy the different components of this project: `exe_agent`, `logs_analyzer`, and `frontend/on-call`.

## 1. `exe_agent`

**Purpose:** A Python component for browser and Command Line Interface (CLI) automation using Selenium.

**Setup & Dependencies:**

1.  Navigate to the `exe_agent` directory.
2.  Install Python dependencies:
    ```bash
    pip install -r exe_agent/requirements.txt
    ```

**Key Deployment Considerations & Recommendations:**

*   **Dependency Management:**
    *   The `exe_agent/requirements.txt` file should be updated to pin specific versions for all dependencies (e.g., `selenium==4.10.0`) to ensure stable deployments.
    *   The `pyyaml` dependency is currently listed but appears unused and should be removed.
*   **WebDriver Setup:**
    *   A compatible WebDriver (e.g., ChromeDriver for Chrome) must be installed in the target environment and accessible via the system's PATH. The WebDriver version must match the installed browser version.
    *   Alternatively, the deployment environment needs internet access for Selenium's `selenium-manager` to attempt automatic driver downloads.
*   **Configuration (Hardcoded Values):**
    *   **Browser Paths**: The component contains hardcoded paths for Chrome/Chromium on macOS. For cross-platform reliability, these should be removed in favor of relying on the WebDriver in PATH, or the browser binary path should be made configurable (e.g., via an environment variable).
    *   **Screenshot Directory**: Screenshots are saved to the current working directory. This should be made a configurable path.
    *   **Timeouts & Sleeps**: Various `time.sleep()` calls and hardcoded timeout values exist. These should be reviewed:
        *   Replace `time.sleep()` in browser interactions with Selenium's explicit waits for more robust automation.
        *   Externalize other significant timeout values (e.g., for API calls, subprocesses) to be configurable.
*   **OS-Specific Features:**
    *   The `run_cli` method includes macOS-specific behavior using `osascript` to open a new Terminal window. This feature will not be available on other operating systems. The core CLI command execution is cross-platform.
*   **Logging:**
    *   The component currently uses `print()` for output. For better diagnostics in production, implement structured logging using Python's `logging` module.

## 2. `logs_analyzer`

**Purpose:** A Flask web application for analyzing log files, featuring an AI agent for insights and automated ticket creation.

**Setup & Dependencies:**

1.  Navigate to the `logs_analyzer` directory.
2.  Install Python dependencies:
    ```bash
    pip install -r logs_analyzer/requirements.txt
    ```
3.  **Environment Variables:**
    *   Set up environment variables as defined in `logs_analyzer/env.example`.
    *   **Crucially, ensure `FLASK_SECRET_KEY` is set to a strong, unique value in your production environment.** This key is vital for session security. (It needs to be added to `env.example`).
    *   `OPENAI_API_KEY` is required for the AI agent functionality.

**Critical Deployment Limitations:**

*   **Not Suitable for Production/Scalable Deployment (Current State):**
    *   The application (`app.py`) relies heavily on **global variables** for managing state (e.g., analysis progress, results, ticket data) and uses a simple `threading.Lock`. This architecture is **not safe for multi-process or multi-worker WSGI deployments** (like Gunicorn with more than one worker). Each worker would have its own independent state, leading to inconsistent user experiences and incorrect behavior.
    *   **Recommendation**: This requires a significant architectural redesign. Options include using an external store for state (e.g., Redis, a database) and a proper task queue (e.g., Celery, RQ) for background analysis tasks and inter-process communication (like the reasoning step stream).
*   **Local File Storage:**
    *   Uploaded log files, generated tickets (`tickets.json`), and knowledge base playbooks (`data/playbooks/`) are stored on the local filesystem relative to the application. This is not suitable for scalable or ephemeral environments (e.g., containers, serverless).
    *   **Recommendation**: Use a shared, persistent storage solution (e.g., AWS S3, Google Cloud Storage, Azure Blob Storage).
*   **Refactoring Status:**
    *   The refactoring of `logs_analyzer/app.py` and `logs_analyzer/services/agent.py` (which contains the core analysis logic) was previously attempted but could not be completed due to tool limitations in applying large/complex changes. The underlying complexity in these files remains.

**Other Deployment Considerations & Recommendations:**

*   **Configuration:**
    *   The path to the `exe_agent` (used for the "Resolution Agent" subprocess) is hardcoded in `app.py` with a relative path (`../exe_agent/demo_run.py`). This is fragile and assumes a specific inter-component directory structure. **Recommendation**: Make this path configurable via an environment variable.
    *   The OpenAI model name used by `LogAnalysisAgent` defaults to a hardcoded value within `services/agent.py`. **Recommendation**: This should be configurable, ideally via an environment variable passed to the agent during its initialization in `app.py`.
    *   Default file paths in `services/ticket_service.py` (for `tickets.json` and playbooks) should be made absolute based on `app.root_path` or `app.instance_path`, or made fully configurable.
*   **Dependency Management:**
    *   Pin all dependency versions in `logs_analyzer/requirements.txt` for stability.
*   **WSGI Server:**
    *   For any use beyond local development, a production-grade WSGI server (e.g., Gunicorn, Waitress) is necessary instead of Flask's built-in development server.
    *   **Warning**: Due to the global state issues mentioned above, running multiple workers with such a server will lead to problems. The application must be refactored first.
*   **Logging:**
    *   The application uses `print()` for much of its logging. **Recommendation**: Implement structured logging using Python's `logging` module throughout the application.

For development and basic local running instructions, see `logs_analyzer/RUNNING.md`.

## 3. `frontend/on-call`

**Purpose:** A React-based Kanban board user interface.

**Build Process:**

1.  Navigate to the `frontend/on-call` directory.
2.  Install dependencies:
    ```bash
    npm install 
    ``` 
    *(Note: `--legacy-peer-deps` might be needed due to `react-beautiful-dnd` compatibility with React 19, as identified in reviews).*
3.  Build for production:
    ```bash
    npm run build
    ```

**Output:**
Static files will be generated in the `frontend/on-call/build/` directory.

**Serving:**
The contents of the `build/` directory can be served by any static web server (e.g., Nginx, Apache, AWS S3, Netlify, Vercel). Ensure the server is configured to serve `index.html` for SPA (Single Page Application) routing if client-side routes are added later.

**Key Deployment Considerations & Recommendations:**

*   **`react-beautiful-dnd` Dependency:**
    *   This library is deprecated and has known peer dependency issues with React 19. This poses a significant maintenance risk.
    *   **Recommendation**: Prioritize migrating to a modern, actively maintained drag-and-drop library (e.g., Dnd Kit).
*   **Data Source:**
    *   The application currently uses static `initialData` embedded in the frontend.
    *   **Recommendation**: If dynamic data persistence is required, a backend API needs to be developed. The frontend would then need to be updated to fetch and update data via this API. API endpoints should be configured using `REACT_APP_` prefixed environment variables (standard Create React App practice).
*   **Environment Variables for API (Future):**
    *   If backend integration is added, API URLs should be configured using environment variables (e.g., `REACT_APP_API_BASE_URL`) and documented.
*   **Client-Side Routing (Future):**
    *   Currently, the application appears to be a single view. If more views/routes are added using React Router, the static server must be configured to redirect all non-asset requests to `index.html`.
```
