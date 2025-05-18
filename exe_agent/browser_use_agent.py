# BrowserUseAgent: An agent that can use the browser to take actions using Selenium.
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import yaml
import subprocess
import requests
import os
from datetime import datetime

class BrowserUseAgent:
    def __init__(self, driver_path=None, headless=True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        # Robust Chromium detection for macOS
        chromium_candidates = [
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/opt/homebrew/bin/chromium',
            '/usr/local/bin/chromium',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
        ]
        chromium_path = None
        for path in chromium_candidates:
            if os.path.exists(path):
                chromium_path = path
                break
        if chromium_path:
            print(f'[INFO] Using Chromium binary at: {chromium_path}')
            options.binary_location = chromium_path
        else:
            print('[WARN] Chromium not found at common paths. Using system default Chrome.')
        self.driver = webdriver.Chrome(driver_path, options=options) if driver_path else webdriver.Chrome(options=options)

    def go_to(self, url):
        print(f"[Browser] Navigating to: {url}")
        self.driver.get(url)
        time.sleep(2)

    def search(self, query, search_box_selector, submit=True):
        print(f"[Browser] Searching for '{query}' in selector '{search_box_selector}'")
        box = self.driver.find_element(By.CSS_SELECTOR, search_box_selector)
        box.clear()
        box.send_keys(query)
        if submit:
            box.send_keys(Keys.RETURN)
        time.sleep(2)

    def click(self, selector):
        print(f"[Browser] Clicking element with selector: {selector}")
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()
        time.sleep(2)

    def get_text(self, selector):
        print(f"[Browser] Getting text from selector: {selector}")
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        text = element.text
        print(f"[Browser] Text found: {text[:200]}{'...' if len(text) > 200 else ''}")
        return text

    def run_instructions_from_file(self, file_path):
        with open(file_path, 'r') as f:
            instructions = yaml.safe_load(f)
        for step in instructions:
            action = step['action']
            if action == 'go_to':
                self.go_to(step['url'])
            elif action == 'search':
                self.search(step['query'], step['search_box_selector'])
            elif action == 'click':
                self.click(step['selector'])
            elif action == 'get_text':
                text = self.get_text(step['selector'])
                print(f"Text from {step['selector']}:\n{text}\n")

    def run_cli(self, command):
        print(f"[CLI] Running command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"[CLI] Output:\n{result.stdout}")
        if result.stderr:
            print(f"[CLI] Error:\n{result.stderr}")
        return result.stdout, result.stderr

    def call_api(self, method, url, **kwargs):
        print(f"[API] Calling {method.upper()} {url} with {kwargs}")
        response = requests.request(method, url, **kwargs)
        print(f"[API] Status: {response.status_code}")
        print(f"[API] Response: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
        return response

    def screenshot(self, name_prefix="screenshot"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name_prefix}_{ts}.png"
        self.driver.save_screenshot(filename)
        print(f"[Browser] Screenshot saved: {filename}")
        return filename

    def run_runbook(self, runbook_path):
        print(f"[Runbook] Executing runbook: {runbook_path}")
        with open(runbook_path, 'r') as f:
            lines = f.readlines()
        current_step = None
        for line in lines:
            line = line.strip('\n')
            if not line.strip():
                continue
            if not line.startswith('ACTION:') and not line.startswith('    ACTION:') and not line.startswith(' '):
                current_step = line.strip(':')
                print(f"\n=== Step: {current_step} ===")
            elif 'ACTION:' in line:
                action_line = line.split('ACTION:')[1].strip()
                parts = action_line.split()
                action = parts[0]
                params = {}
                for p in parts[1:]:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        v = v.strip('"')
                        params[k] = v
                try:
                    if action == 'go_to':
                        self.go_to(params['url'])
                        self.screenshot(current_step.replace(' ', '_'))
                    elif action == 'search':
                        self.search(params['query'], params['search_box_selector'])
                        self.screenshot(current_step.replace(' ', '_'))
                    elif action == 'click':
                        self.click(params['selector'])
                        self.screenshot(current_step.replace(' ', '_'))
                    elif action == 'get_text':
                        text = self.get_text(params['selector'])
                        print(f"[Runbook] Text from {params['selector']}:\n{text}\n")
                        self.screenshot(current_step.replace(' ', '_'))
                    elif action == 'cli':
                        self.run_cli(params['command'])
                    elif action == 'api':
                        method = params.get('method', 'get')
                        url = params['url']
                        self.call_api(method, url)
                except Exception as e:
                    print(f"[ERROR] Failed to execute action '{action}' in step '{current_step}': {e}")

    def close(self):
        self.driver.quit()
