"""
Demonstrates the capabilities of the BrowserUseAgent by executing a predefined runbook.
"""
import os
from exe_agent.browser_use_agent import BrowserUseAgent # Corrected import path

def run_demo():
    """
    Initializes the BrowserUseAgent, runs a demo runbook, and closes the agent.
    The agent is run in non-headless mode for this demonstration.
    """
    print("Starting BrowserUseAgent demo...")
    agent = BrowserUseAgent(headless=False)
    try:
        # Construct the absolute path to demo_runbook.txt relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        runbook_path = os.path.join(current_dir, 'demo_runbook.txt')

        print(f"Executing runbook: {runbook_path}")
        agent.run_runbook(runbook_path)
        print("Runbook execution finished.")
    except Exception as e: # pylint: disable=broad-except
        print(f"An error occurred during the demo: {e}")
    finally:
        print("Closing agent...")
        agent.close()
        print("Demo finished.")

if __name__ == "__main__":
    run_demo()
