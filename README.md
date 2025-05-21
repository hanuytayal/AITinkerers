# Project: Automated System & Database Troubleshooting Demo

## Overview
This project demonstrates an automated troubleshooting workflow for system and database issues using a Python Selenium agent, a robust runbook, a React-based frontend for on-call task management, and a Flask-based log analyzer for deeper diagnostics. The system executes both web and CLI actions, collects diagnostics, and provides a user-friendly interface for rapid incident response.

## Configuration
For local development, copy the `.env.example` file to a new file named `.env` in the project root:
```sh
cp .env.example .env
```
Edit the `.env` file to include your actual `OPENAI_API_KEY`.

The application uses `python-dotenv` to load these variables from the `.env` file during local development.
The `OPENAI_API_KEY` is essential for the log analysis features provided by the `/log_analyzer` endpoints.
When deploying via Docker, these configurations will typically be passed as environment variables to the Docker container.

## Key Components
- **Runbook (`exe_agent/demo_runbook.txt`)**: Defines a reliable sequence of troubleshooting steps, including:
  - Checking GitHub status (web)
  - Checking disk space (CLI)
  - Checking Docker/Postgres status and logs (CLI)
  - Exporting results and screenshots
- **Agent (`exe_agent/browser_use_agent.py`)**: Executes runbook actions, manages browser and CLI tasks, and handles resource cleanup.
- **Demo Runner (`exe_agent/demo_run.py`)**: Runs the agent with the runbook for demonstration.
- **Frontend (`frontend/on-call/`)**: React app for on-call task management, Kanban board, and incident tracking. Integrates with backend for live updates.
- **Log Analyzer (`api_handlers/log_analyzer_router.py` within FastAPI)**: Integrated into the main FastAPI application for log ingestion, analysis, and ticketing.
- **Screenshots & Results**: Diagnostic screenshots and result files are saved in `exe_agent/screenshots/` and `diagnostic_results/` (relevant to the standalone `exe_agent` if used separately).

## How to Run the Demo
1. **Set up environment variables:**
   - Ensure you have created and configured your `.env` file as described in the "Configuration" section.
2. **Install agent dependencies:**
   ```sh
   cd exe_agent
   pip install -r requirements.txt
   ```
2. **Run the agent demo:**
   ```sh
   python demo_run.py
   ```
3. **Run the log analyzer backend:**
   ```sh
   cd logs_analyzer
   pip install -r requirements.txt
   # python run.py # This is now part of the FastAPI app
   ```
4. **Install main application dependencies:**
   ```sh
   pip install -r requirements.txt 
   ```
5. **Run the FastAPI application:**
   ```sh
   uvicorn main:app --reload
   ```
   The application will typically be available at `http://127.0.0.1:8000`. The `/log_analyzer` endpoints will be under this base URL (e.g., `http://127.0.0.1:8000/log_analyzer/analyze_log`).

6. **Run the frontend (on-call dashboard):**
   ```sh
   cd frontend/on-call
   npm install
   npm start
   ```
7. **Review results:**
   - Log analysis: Access the FastAPI endpoints (e.g., using a tool like Postman or curl, or eventually through the frontend).
   - Screenshots: `exe_agent/screenshots/` or `diagnostic_results/` (if running the standalone agent demo)
   - Diagnostic text: `investigation_results.txt` (if running the standalone agent demo)
   - On-call board: `frontend/on-call/` web UI

## Design Principles
- **Reliability:** Only robust, repeatable actions are included in the runbook.
- **Simplicity:** The workflow is concise and easy to extend.
- **Documentation:** All steps and architecture are documented for clarity.
- **Separation of Concerns:** Agent, frontend, and log analyzer are modular and can be used independently or together.

## Project Structure
- `api_handlers/` — Contains FastAPI routers and service logic for different API functionalities.
- `exe_agent/` — Agent logic, runbook, and demo runner (can be used standalone).
- `frontend/on-call/` — React frontend for on-call/incident management.
- `logs_analyzer/` — Original Flask backend for log analysis (now being integrated into FastAPI).
- `main.py` — The main FastAPI application file.
- `requirements.txt` — Main Python dependencies for the FastAPI application.
- `.env.example` — Example environment variable configuration.
- `README.md` — Project overview and instructions.
- `ARCHITECTURE.md` — System architecture and workflow.

## Further Improvements
- Add advanced error handling
- Expand runbook and playbook scenarios
- Integrate agent with frontend/backend for live troubleshooting
- Enhance log analysis and ticketing automation

---
For architecture details, see `ARCHITECTURE.md`.

## Deploying to AWS EC2 with Docker

This section guides you through deploying the AITinkerers FastAPI application to an AWS EC2 instance using Docker.

**1. Prerequisites:**
- An AWS EC2 instance is set up and accessible via SSH.
- Docker is installed on the EC2 instance.
    - For Amazon Linux 2, you can follow instructions here: [Install Docker on Amazon Linux 2](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/docker-basics.html#install_docker_AL2).
    - For other Linux distributions, refer to the official Docker installation guide: [Install Docker Engine](https://docs.docker.com/engine/install/).
- The EC2 instance's Security Group is configured to allow inbound TCP traffic on port 8000 (or the port you intend to use).

**2. Setup on EC2 Instance:**
- Connect to your EC2 instance:
  ```bash
  ssh -i /path/to/your-key.pem ec2-user@your_ec2_public_ip
  ```
- Clone the repository:
  ```bash
  git clone https://github.com/hanuytayal/AITinkerers.git
  cd AITinkerers
  ```
- (Optional but recommended for simplicity in this guide) Create a `.env` file on the EC2 instance for your `OPENAI_API_KEY`.
  ```bash
  echo "OPENAI_API_KEY=your_actual_openai_api_key_here" > .env
  ```
  *Security Note: For production environments, consider using AWS Secrets Manager or AWS Systems Manager Parameter Store for managing sensitive information like API keys instead of storing them in a plain text `.env` file on the instance.*

**3. Build the Docker Image:**
- Ensure you are in the root directory of the cloned repository (`AITinkerers`).
- Build the Docker image:
  ```bash
  docker build -t aitinkerers-app .
  ```

**4. Run the Docker Container:**
- Run the Docker container. The application listens on port 8000 by default (as defined in the Dockerfile).
  ```bash
  docker run -d -p 8000:8000 --name aitinkerers-container \
             -e OPENAI_API_KEY="your_actual_openai_api_key_here" \
             aitinkerers-app
  ```
- **Explanation of the command:**
    - `-d`: Runs the container in detached mode (in the background).
    - `-p 8000:8000`: Maps port 8000 of the host EC2 instance to port 8000 of the container.
    - `--name aitinkerers-container`: Assigns a name to the container for easier management.
    - `-e OPENAI_API_KEY="your_actual_openai_api_key_here"`: Sets the `OPENAI_API_KEY` environment variable inside the container. Replace `your_actual_openai_api_key_here` with your valid key.

- **Alternative using an `.env` file (if created in Step 2):**
  ```bash
  # Ensure your .env file is in the current directory (AITinkerers/)
  docker run -d -p 8000:8000 --name aitinkerers-container \
             --env-file .env \
             aitinkerers-app
  ```

**5. Accessing the Application:**
- Once the container is running, the application should be accessible via your EC2 instance's public IP address or DNS name on port 8000.
    - Example: `http://<your_ec2_public_ip>:8000/`
- You can test specific endpoints:
    - Main welcome: `http://<your_ec2_public_ip>:8000/`
    - Log Analyzer health: `http://<your_ec2_public_ip>:8000/log_analyzer/log_analyzer_health`

**6. Managing the Container:**
- **View running containers:**
  ```bash
  docker ps
  ```
- **View container logs (useful for debugging):**
  ```bash
  docker logs aitinkerers-container
  ```
- **Stop the container:**
  ```bash
  docker stop aitinkerers-container
  ```
- **Remove the container (after stopping):**
  ```bash
  docker rm aitinkerers-container
  ```

## Running Tests

This project uses `pytest` for running unit and integration tests.

**1. Prerequisites:**
- Ensure you have installed the development dependencies, including `pytest`. If you installed dependencies from `requirements.txt`, `pytest` should be included:
  ```bash
  pip install -r requirements.txt
  ```
  Or, install `pytest` separately:
  ```bash
  pip install pytest
  ```

**2. Running Tests:**
- Navigate to the project root directory (where `pytest.ini` is located).
- Run the tests using the following command:
  ```bash
  pytest
  ```
- Pytest will automatically discover and run tests from files named `test_*.py` or `*_test.py` in the `tests` directory and its subdirectories.

The tests for the `/log_analyzer` API endpoints are located in `tests/test_log_analyzer_api.py`.