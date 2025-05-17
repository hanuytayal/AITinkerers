import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs/agent.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ai_agent')

class AIAgent:
    """
    AI Agent that can execute CLI commands, interact with browsers, and make API calls.
    Records all actions and responses for analysis.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the AI agent with optional configuration.
        
        Args:
            config_path: Path to the configuration file (JSON format)
        """
        self.config = {}
        self.history = []
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
                logger.info(f"Loaded configuration from {config_path}")
        
        # Create task ID for this agent session
        self.task_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Agent initialized with task ID: {self.task_id}")
    
    def execute_cli_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a CLI command and record the result.
        
        Args:
            command: The CLI command to execute
            
        Returns:
            Dictionary containing the command, output, exit code and timestamp
        """
        import subprocess
        
        logger.info(f"Executing CLI command: {command}")
        
        try:
            # Execute the command and capture output
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            # Record the result
            result = {
                "type": "cli",
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "timestamp": datetime.now().isoformat(),
                "success": exit_code == 0
            }
            
            self.history.append(result)
            
            if exit_code == 0:
                logger.info(f"Command executed successfully: {command}")
            else:
                logger.warning(f"Command failed with exit code {exit_code}: {command}")
                logger.warning(f"Error: {stderr}")
            
            return result
        
        except Exception as e:
            error_result = {
                "type": "cli",
                "command": command,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
            self.history.append(error_result)
            logger.error(f"Exception executing command '{command}': {str(e)}")
            return error_result
    
    def make_api_request(self, url: str, method: str = "GET", headers: Dict = None, 
                        data: Any = None, params: Dict = None, json_data: Dict = None) -> Dict[str, Any]:
        """
        Make an API request and record the response.
        
        Args:
            url: The URL to make the request to
            method: The HTTP method (GET, POST, PUT, DELETE, etc.)
            headers: Request headers
            data: Request body data
            params: Query parameters
            json_data: JSON data for request body
            
        Returns:
            Dictionary containing the request details, response, and timestamp
        """
        import requests
        
        headers = headers or {}
        logger.info(f"Making {method} request to {url}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                params=params,
                json=json_data,
                timeout=30
            )
            
            # Try to parse response as JSON, fallback to text if not JSON
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            # Record the result
            result = {
                "type": "api",
                "url": url,
                "method": method,
                "headers": headers,
                "data": data,
                "params": params,
                "json_data": json_data,
                "status_code": response.status_code,
                "response": response_data,
                "timestamp": datetime.now().isoformat(),
                "success": response.status_code < 400
            }
            
            self.history.append(result)
            
            if response.status_code < 400:
                logger.info(f"API request successful: {method} {url} (Status: {response.status_code})")
            else:
                logger.warning(f"API request failed: {method} {url} (Status: {response.status_code})")
            
            return result
            
        except Exception as e:
            error_result = {
                "type": "api",
                "url": url,
                "method": method,
                "headers": headers,
                "data": data,
                "params": params,
                "json_data": json_data,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
            self.history.append(error_result)
            logger.error(f"Exception making API request to {url}: {str(e)}")
            return error_result
    
    def browser_action(self, action: str, url: Optional[str] = None, 
                     selectors: Optional[List[str]] = None, inputs: Optional[Dict[str, str]] = None,
                     wait_time: int = 3) -> Dict[str, Any]:
        """
        Perform browser actions using Playwright.
        
        Args:
            action: Type of action ('navigate', 'click', 'input', 'screenshot', 'extract')
            url: URL to navigate to
            selectors: CSS selectors to interact with
            inputs: Dictionary of {selector: input_value} for input actions
            wait_time: Time to wait after action in seconds
            
        Returns:
            Dictionary containing the action details, result, and timestamp
        """
        from playwright.sync_api import sync_playwright
        import time
        import base64
        
        logger.info(f"Performing browser action: {action}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                result = {
                    "type": "browser",
                    "action": action,
                    "url": url,
                    "selectors": selectors,
                    "inputs": inputs,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
                
                # Handle different action types
                if action == "navigate" and url:
                    page.goto(url)
                    result["title"] = page.title()
                    
                elif action == "click" and selectors:
                    page.goto(url) if url else None
                    for selector in selectors:
                        page.click(selector)
                        time.sleep(1)  # Short delay between clicks
                    
                elif action == "input" and inputs:
                    page.goto(url) if url else None
                    for selector, value in inputs.items():
                        page.fill(selector, value)
                    
                elif action == "screenshot":
                    page.goto(url) if url else None
                    screenshot = page.screenshot()
                    screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                    result["screenshot"] = screenshot_base64
                    
                    # Save screenshot to disk
                    screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs/screenshots')
                    os.makedirs(screenshots_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshots_dir, f"{self.task_id}-{int(time.time())}.png")
                    with open(screenshot_path, 'wb') as f:
                        f.write(screenshot)
                    
                    result["screenshot_path"] = screenshot_path
                
                elif action == "extract" and selectors:
                    page.goto(url) if url else None
                    extracted_data = {}
                    
                    for selector in selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            extracted_data[selector] = [element.inner_text() for element in elements]
                        except Exception as e:
                            extracted_data[selector] = f"Error extracting: {str(e)}"
                    
                    result["extracted_data"] = extracted_data
                
                # Wait for specified time
                time.sleep(wait_time)
                
                # Close browser
                browser.close()
                
                self.history.append(result)
                logger.info(f"Browser action '{action}' completed successfully")
                
                return result
                
        except Exception as e:
            error_result = {
                "type": "browser",
                "action": action,
                "url": url,
                "selectors": selectors,
                "inputs": inputs,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
            self.history.append(error_result)
            logger.error(f"Exception performing browser action '{action}': {str(e)}")
            return error_result
    
    def save_history(self, output_path: Optional[str] = None) -> str:
        """
        Save the agent's action history to a JSON file.
        
        Args:
            output_path: Path to save the history file (optional)
            
        Returns:
            Path to the saved history file
        """
        if not output_path:
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            output_path = os.path.join(logs_dir, f"{self.task_id}-history.json")
        
        with open(output_path, 'w') as f:
            json.dump({
                "task_id": self.task_id,
                "start_time": self.history[0]["timestamp"] if self.history else datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "actions": self.history
            }, f, indent=2)
        
        logger.info(f"History saved to {output_path}")
        return output_path
    
    def run_task(self, task_function) -> None:
        """
        Run a task function with the agent as its argument.
        
        Args:
            task_function: Function that takes an agent instance and executes a task
        """
        try:
            logger.info(f"Starting task execution")
            task_function(self)
            logger.info(f"Task execution completed")
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
        finally:
            self.save_history() 