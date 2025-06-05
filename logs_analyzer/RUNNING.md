# How to Run the Log Analysis Agent

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- OpenAI API key (for full functionality)

## Setup Steps

1. **Create and activate a virtual environment**

   On macOS/Linux:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

   On Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies**

   ```
   pip install -r requirements.txt
   ```

3. **Set up OpenAI API Key**

   The application uses the OpenAI API for intelligent log analysis with their reasoning models. You need to provide your API key:

   Option 1: Set it as an environment variable
   
   On macOS/Linux:
   ```
   export OPENAI_API_KEY=your_api_key_here
   ```

   On Windows:
   ```
   set OPENAI_API_KEY=your_api_key_here
   ```

   Option 2: Create a `.env` file
   ```
   cp env.example .env
   ```
   Then edit the `.env` file to add your API key.

   Additionally, for security, especially if running in any shared or non-development environment, set the `FLASK_SECRET_KEY`:
   ```bash
   # On macOS/Linux
   export FLASK_SECRET_KEY='a_very_strong_and_unique_secret_key_here'
   # On Windows (Command Prompt)
   # set FLASK_SECRET_KEY=a_very_strong_and_unique_secret_key_here
   # On Windows (PowerShell)
   # $env:FLASK_SECRET_KEY='a_very_strong_and_unique_secret_key_here'
   ```
   Or add `FLASK_SECRET_KEY='your_secret_key'` to your `.env` file. A default key is used if this is not set, which is insecure for anything beyond local testing.

## Running the Application

1. **Standard method**

   ```
   python run.py
   ```

   This will start the Flask development server. You can access the application at http://127.0.0.1:5000

2. **Alternative method using Flask CLI**

   ```
   flask --app app run
   ```

   For debug mode:
   ```
   flask --app app run --debug
   ```

## Using the Example Log File

To use the provided example log file:

```
python setup_example.py
```

This will copy the example log file (`oom.csv`) to the uploads directory, making it available for analysis within the application.

## Automatic Ticket Creation

The application now automatically creates tickets for:
- Issues with FATAL severity
- That have occurred 5 or more times

Tickets are created using function calling after the AI completes its reasoning process, ensuring that tickets are only created once the analysis is fully completed.

## Real-Time Reasoning Display

The application displays the AI's reasoning process in real-time:
1. Upload a log file
2. Watch as the AI analyzes the log data step-by-step
3. Observe as the reasoning completes and tickets are created
4. The page updates automatically to show new reasoning steps as they happen

## Troubleshooting

- **No API Key**: If you run the application without an OpenAI API key, it will fall back to mock analysis mode. This is useful for testing but won't provide the full capabilities of the agent.

- **File Upload Issues**: Make sure the uploads directory exists and is writable.

- **Import Errors**: Verify that all dependencies were installed correctly.

- **OpenAI API Errors**: If you encounter errors with the OpenAI API, verify your API key and check that you have access to the o4-mini model.

## Viewing the Application

Once the application is running, open your web browser and navigate to:

```
http://127.0.0.1:5000
```

You should see the Log Analysis Agent interface where you can upload log files for automated analysis.

## Production Considerations (Important Warnings)

- **WSGI Server**: The Flask development server (`python run.py` or `flask run`) is **not suitable for production use**. For deployment, use a production-grade WSGI server like Gunicorn or Waitress. Example with Gunicorn:
  ```bash
  gunicorn --workers 4 --bind 0.0.0.0:5000 run:app
  ```
  *(Adjust `run:app` if your Flask application instance is named differently or located in a different file within your `run.py` or `app.py`)*.

- **Critical Limitation - Global State & Scalability**: This application, in its current state, uses global variables within `app.py` to manage analysis state, progress, and results. This architecture makes it **unsuitable for running with multiple worker processes** (e.g., `gunicorn --workers 4` or any other multi-process WSGI setup). Each worker would have an independent copy of the application's state, leading to inconsistent user experiences, lost data between requests handled by different workers, and incorrect behavior.
  - **Recommendation**: Before any production deployment that requires handling more than one request at a time or scaling beyond a single worker, the application requires significant architectural changes. This includes externalizing state management (e.g., using Redis, a database, or a proper task queue system like Celery) and ensuring inter-process communication for features like the reasoning stream. The refactoring to address these fundamental issues was not completed in prior tasks.

- **File Storage**: Uploaded files and generated data (like `tickets.json`) are stored on the local filesystem. For production or scalable deployments (especially in containerized or ephemeral environments), consider using a shared, persistent storage solution (e.g., AWS S3, Google Cloud Storage, Azure Blob Storage).
