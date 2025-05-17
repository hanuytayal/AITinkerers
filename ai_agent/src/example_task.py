"""
Example task for the AI Agent.
This task demonstrates how to use the agent to:
1. Execute CLI commands
2. Make API requests
3. Perform browser actions
"""

import os
import time
from src.agent import AIAgent

def example_task(agent: AIAgent):
    """
    Example task that demonstrates the agent's capabilities.
    
    Args:
        agent: Instance of the AIAgent
    """
    # Execute CLI commands
    agent.execute_cli_command("echo 'Hello from AI Agent'")
    agent.execute_cli_command("ls -la")
    agent.execute_cli_command("python3 --version")
    
    # Make API requests
    agent.make_api_request(
        url="https://httpbin.org/get",
        method="GET",
        params={"param1": "value1", "param2": "value2"}
    )
    
    agent.make_api_request(
        url="https://httpbin.org/post",
        method="POST",
        json_data={"key1": "value1", "key2": "value2"}
    )
    
    # Perform browser actions
    
    # Navigate to a website
    agent.browser_action(
        action="navigate",
        url="https://example.com"
    )
    
    # Take a screenshot
    agent.browser_action(
        action="screenshot",
        url="https://news.ycombinator.com"
    )
    
    # Extract content from a page
    agent.browser_action(
        action="extract",
        url="https://news.ycombinator.com",
        selectors=[".title a", ".subtext"]
    )
    
    # Fill out a form (example with DuckDuckGo search)
    agent.browser_action(
        action="input",
        url="https://duckduckgo.com",
        inputs={"input[name='q']": "python automation"}
    )
    
    agent.browser_action(
        action="click",
        selectors=["button[type='submit']"]
    )
    
    # Take a screenshot of the search results
    time.sleep(2)  # Wait for results to load
    agent.browser_action(
        action="screenshot"
    )
    
    print(f"Task completed. Check logs at {os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')}")

if __name__ == "__main__":
    # Create the agent with the default config
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config/default_config.json')
    agent = AIAgent(config_path=config_path)
    
    # Run the example task
    agent.run_task(example_task) 