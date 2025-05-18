import os
from browser_use_agent import BrowserUseAgent

def run_demo():
    agent = BrowserUseAgent(headless=False)
    agent.run_runbook(os.path.join(os.path.dirname(__file__), 'demo_runbook.txt'))
    agent.close()

if __name__ == "__main__":
    run_demo()
