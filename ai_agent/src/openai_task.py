"""
OpenAI-powered task for the AI Agent.
This task demonstrates how to use OpenAI to make decisions based on data gathered by the agent.
"""

import os
import json
import time
from typing import List, Dict, Any
from src.agent import AIAgent
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Get OpenAI API key from environment or config
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def get_openai_client(agent: AIAgent):
    """Get an OpenAI client using either environment variable or agent config."""
    api_key = OPENAI_API_KEY
    
    # If not in environment, try to get from agent config
    if not api_key and agent.config.get("api_keys", {}).get("openai"):
        api_key = agent.config["api_keys"]["openai"]
    
    if not api_key:
        raise ValueError("OpenAI API key not found in environment or agent config")
    
    return OpenAI(api_key=api_key)

def get_llm_decision(client: OpenAI, prompt: str) -> str:
    """
    Get a decision from OpenAI's language model.
    
    Args:
        client: OpenAI client
        prompt: The prompt to send to the LLM
        
    Returns:
        The LLM's response text
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that helps analyze data and make decisions. Provide clear, concise responses."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=1000
    )
    
    return response.choices[0].message.content.strip()

def extract_github_info(agent: AIAgent, repo_owner: str, repo_name: str) -> Dict[str, Any]:
    """
    Extract information about a GitHub repository.
    
    Args:
        agent: AIAgent instance
        repo_owner: Owner of the repository
        repo_name: Name of the repository
        
    Returns:
        Dictionary with repository information
    """
    # Get repository information
    repo_response = agent.make_api_request(
        url=f"https://api.github.com/repos/{repo_owner}/{repo_name}",
        method="GET",
        headers={"Accept": "application/vnd.github.v3+json"}
    )
    
    # Get recent commits
    commits_response = agent.make_api_request(
        url=f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits",
        method="GET",
        headers={"Accept": "application/vnd.github.v3+json"},
        params={"per_page": 5}
    )
    
    # Get open issues
    issues_response = agent.make_api_request(
        url=f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues",
        method="GET",
        headers={"Accept": "application/vnd.github.v3+json"},
        params={"state": "open", "per_page": 5}
    )
    
    return {
        "repository": repo_response.get("response", {}),
        "recent_commits": commits_response.get("response", []),
        "open_issues": issues_response.get("response", [])
    }

def analyze_webpage_content(agent: AIAgent, url: str) -> Dict[str, Any]:
    """
    Analyze the content of a webpage.
    
    Args:
        agent: AIAgent instance
        url: URL of the webpage to analyze
        
    Returns:
        Dictionary with extracted content
    """
    # Navigate to the webpage
    agent.browser_action(
        action="navigate",
        url=url
    )
    
    # Take a screenshot
    screenshot_result = agent.browser_action(
        action="screenshot",
        url=url
    )
    
    # Extract content
    extract_result = agent.browser_action(
        action="extract",
        selectors=["h1", "h2", "p", "a"]
    )
    
    return {
        "url": url,
        "title": extract_result.get("title", ""),
        "headings": extract_result.get("extracted_data", {}).get("h1", []) + 
                    extract_result.get("extracted_data", {}).get("h2", []),
        "paragraphs": extract_result.get("extracted_data", {}).get("p", []),
        "links": extract_result.get("extracted_data", {}).get("a", []),
        "screenshot_path": screenshot_result.get("screenshot_path", "")
    }

def openai_powered_task(agent: AIAgent):
    """
    Task that uses OpenAI to make decisions based on data gathered by the agent.
    
    Args:
        agent: AIAgent instance
    """
    try:
        # Initialize OpenAI client
        client = get_openai_client(agent)
        
        # 1. Collect system information using CLI
        print("Collecting system information...")
        os_info = agent.execute_cli_command("uname -a")
        disk_info = agent.execute_cli_command("df -h")
        memory_info = agent.execute_cli_command("free -h")
        
        # 2. Extract GitHub repository information
        print("Extracting GitHub repository information...")
        repo_owner = "openai"
        repo_name = "openai-python"
        github_info = extract_github_info(agent, repo_owner, repo_name)
        
        # 3. Analyze a webpage
        print("Analyzing webpage content...")
        webpage_info = analyze_webpage_content(agent, "https://openai.com/blog")
        
        # 4. Use OpenAI to analyze the collected data
        print("Generating analysis with OpenAI...")
        
        system_prompt = f"""
        Analyze the following system information and provide a brief summary:
        
        OS Info:
        {os_info.get('stdout', '')}
        
        Disk Info:
        {disk_info.get('stdout', '')}
        
        Memory Info:
        {memory_info.get('stdout', '')}
        """
        
        github_prompt = f"""
        Analyze the following GitHub repository information and provide a brief summary:
        
        Repository: {repo_owner}/{repo_name}
        Description: {github_info['repository'].get('description', 'No description')}
        Stars: {github_info['repository'].get('stargazers_count', 0)}
        Forks: {github_info['repository'].get('forks_count', 0)}
        Open Issues: {github_info['repository'].get('open_issues_count', 0)}
        
        Recent Commits:
        {json.dumps(github_info['recent_commits'], indent=2)[:500]}...
        
        Recent Open Issues:
        {json.dumps(github_info['open_issues'], indent=2)[:500]}...
        """
        
        webpage_prompt = f"""
        Analyze the following webpage content and provide a brief summary:
        
        URL: {webpage_info['url']}
        Title: {webpage_info['title']}
        
        Headings:
        {json.dumps(webpage_info['headings'], indent=2)}
        
        Sample Paragraphs:
        {json.dumps(webpage_info['paragraphs'][:3], indent=2)}
        
        Number of Links: {len(webpage_info['links'])}
        """
        
        # Get analyses from OpenAI
        system_analysis = get_llm_decision(client, system_prompt)
        github_analysis = get_llm_decision(client, github_prompt)
        webpage_analysis = get_llm_decision(client, webpage_prompt)
        
        # 5. Generate final report
        final_prompt = f"""
        Based on the analyses below, create a comprehensive report:
        
        System Analysis:
        {system_analysis}
        
        GitHub Repository Analysis:
        {github_analysis}
        
        Webpage Analysis:
        {webpage_analysis}
        
        Format the report with proper sections, bullet points, and conclusions.
        """
        
        final_report = get_llm_decision(client, final_prompt)
        
        # Save final report to a file
        report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', f"{agent.task_id}-report.md")
        with open(report_path, 'w') as f:
            f.write(final_report)
        
        print(f"Report generated and saved to {report_path}")
        
    except Exception as e:
        print(f"Error during task execution: {str(e)}")

if __name__ == "__main__":
    # Create the agent with the default config
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config/default_config.json')
    agent = AIAgent(config_path=config_path)
    
    # Run the OpenAI-powered task
    agent.run_task(openai_powered_task) 