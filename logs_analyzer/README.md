# Log Analysis Agent

A Flask application that uses OpenAI API to analyze log files and automatically create tickets for oncall engineers.

## Features

- Upload and analyze log files (CSV format)
- AI-powered log analysis using OpenAI's reasoning models
- Identification of critical issues in logs
- Automatic ticket creation for FATAL issues occurring 5+ times
- Real-time visualization of agent reasoning process
- Assignment of tickets to the appropriate oncall engineers

## How It Works

The application uses OpenAI's reasoning model to:

1. Analyze log files to identify critical issues
2. Filter for FATAL severity issues that occurred at least 5 times
3. Complete the reasoning process with detailed step-by-step analysis 
4. Use function calling to create tickets only after reasoning is complete
5. Assign tickets to appropriate oncall engineers based on the service
6. Show the AI's reasoning process in real-time

## Installation

1. Clone this repository
2. Create a virtual environment (recommended)
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required packages
   ```
   pip install -r requirements.txt
   ```
4. Set your OpenAI API key
   ```
   export OPENAI_API_KEY=your_api_key_here
   ```
   (On Windows: `set OPENAI_API_KEY=your_api_key_here`)

## Usage

1. Start the Flask application
   ```
   python run.py
   ```
2. Open your browser and navigate to `http://127.0.0.1:5000/`
3. Upload a log file (CSV format) that includes at least these columns:
   - timestamp
   - service
   - level
   - message
4. The AI agent will analyze the logs and identify critical issues
5. Tickets will be automatically created for FATAL issues occurring 5+ times
6. The reasoning process is displayed in real-time on the results page

## Log File Format

The application expects CSV files with at least the following columns:
- `timestamp`: The time when the log entry was created
- `service`: The name of the service that generated the log
- `level`: The log level (DEBUG, INFO, WARN, ERROR, FATAL)
- `message`: The log message content

Example:
```
timestamp,service,level,message
2025-05-17T20:39:15.921897,gateway,DEBUG,Request routed to payment-service
2025-05-17T20:39:18.921897,inventory-service,DEBUG,Low stock warning
2025-05-17T20:39:19.921897,inventory-service,WARN,Warehouse unreachable
```

## Development

### Project Structure

- `app.py`: Main Flask application
- `services/`: Core application services
  - `agent.py`: Log analysis agent using OpenAI's reasoning model
  - `ticket_service.py`: Service for creating and managing tickets
  - `file_utils.py`: Utilities for file operations
- `templates/`: HTML templates for the web interface
  - `layout.html`: Base template
  - `index.html`: Home page
  - `results.html`: Combined analysis and tickets page
- `static/`: Static assets like CSS and JavaScript files
- `uploads/`: Directory for uploaded log files

### AI Reasoning Model

The application uses OpenAI's reasoning model (`o4-mini`) for:
- Step-by-step analysis of log patterns
- Identification of critical issues
- Determination of issue severity and impact
- Generation of recommended actions

The reasoning process is displayed in real-time in the web interface.

### Development Environment

For development, you can run the application in debug mode:
```
flask --app app run --debug
```

## Testing Without OpenAI API

If no API key is provided, the application will use mock analysis mode, which:
- Simulates the analysis process
- Identifies FATAL log entries that occur 5+ times
- Creates tickets for these issues
- Shows mock reasoning steps

This is useful for testing and development.

## License

MIT 