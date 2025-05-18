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
