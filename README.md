# AI Agent

An AI agent system capable of executing CLI commands, browser actions, and API requests. This agent records all actions and their responses for analysis and reporting.

## Features

- **CLI Interaction**: Execute shell commands and capture outputs
- **Browser Automation**: Navigate websites, take screenshots, extract data, and interact with forms
- **API Integration**: Make HTTP requests to external services
- **Comprehensive Logging**: Record all actions and responses for analysis
- **Configurable**: Use configuration files to customize agent behavior
- **Task-based**: Organize sequences of actions into task functions

## Installation

1. Clone this repository
```
git clone <repository-url>
cd ai-agent
```

2. Create and activate a virtual environment
```
python3 -m venv ai-agent-env
source ai-agent-env/bin/activate  # On Windows, use: ai-agent-env\Scripts\activate
```

3. Install dependencies
```
pip install requests selenium openai langchain python-dotenv playwright
```

4. Install Playwright browsers
```
playwright install
```

## Configuration

The agent uses a configuration file located at `ai_agent/config/default_config.json`.
You can modify this file to:

- Add API keys
- Configure browser behavior
- Set up logging preferences
- Define safe CLI commands
- Set retry policies

Make a copy of the default config and modify as needed:
```
cp ai_agent/config/default_config.json ai_agent/config/my_config.json
```

## Usage

1. Create a task function that defines the actions for the agent to perform:

```python
def my_task(agent):
    # Execute CLI commands
    agent.execute_cli_command("ls -la")
    
    # Make API requests
    agent.make_api_request(
        url="https://api.example.com/endpoint",
        method="GET",
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    
    # Perform browser actions
    agent.browser_action(
        action="navigate",
        url="https://example.com"
    )
    
    agent.browser_action(
        action="screenshot",
        url="https://example.com"
    )
```

2. Run the task with the agent:

```python
from ai_agent.src.agent import AIAgent

# Create the agent with custom config
agent = AIAgent(config_path="path/to/config.json")

# Run the task
agent.run_task(my_task)
```

## Example

Check out `ai_agent/src/example_task.py` for a complete example of using the agent to:
- Execute CLI commands
- Make API requests to httpbin
- Navigate to websites
- Take screenshots
- Extract data
- Fill out forms

Run the example:
```
cd ai_agent
python -m src.example_task
```

## Project Structure

```
ai_agent/
├── config/
│   └── default_config.json
├── logs/
│   ├── agent.log
│   ├── task-YYYYMMDD-HHMMSS-history.json
│   └── screenshots/
├── src/
│   ├── agent.py
│   └── example_task.py
└── README.md
```

## Customization

The agent can be extended with additional capabilities by adding methods to the `AIAgent` class. Some ideas for extension:

- AI-powered decision making using LLMs
- Natural language processing for command generation
- Image recognition for browser automation
- Integration with specific services (GitHub, JIRA, etc.)
- Custom reporting and visualization

## License

MIT