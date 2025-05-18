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
        self.headless = headless
        self.setup_browser_options()
        self.current_url = None

    def setup_browser_options(self):
        self.options = webdriver.ChromeOptions()
        if self.headless:
            self.options.add_argument('--headless=new')  # Updated headless argument
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        
        # Chrome/Chromium detection for macOS
        chrome_candidates = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/opt/homebrew/bin/chrome',
            '/opt/homebrew/bin/chromium',
        ]
        browser_path = None
        for path in chrome_candidates:
            if os.path.exists(path):
                browser_path = path
                break
                
        if browser_path:
            self.options.binary_location = browser_path

    def get_new_driver(self):
        try:
            driver = webdriver.Chrome(options=self.options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            print(f"Error initializing Chrome driver: {str(e)}")
            print("Trying to install webdriver using selenium-manager...")
            try:
                driver = webdriver.Chrome(options=self.options)
                driver.implicitly_wait(10)
                return driver
            except Exception as e2:
                raise Exception(f"Failed to initialize Chrome driver: {str(e2)}")

    def go_to(self, url, driver=None):
        print(f"[Browser] Navigating to: {url}")
        if driver is None:
            driver = self.get_new_driver()
        try:
            driver.get(url)
            self.current_url = url
            time.sleep(2)
            return driver
        except Exception as e:
            print(f"Error navigating to {url}: {str(e)}")
            driver.quit()
            raise

    def search(self, query, search_box_selector, submit=True):
        print(f"[Browser] Searching for '{query}' in selector '{search_box_selector}'")
        driver = self.get_new_driver()
        try:
            driver.get(self.current_url)
            box = driver.find_element(By.CSS_SELECTOR, search_box_selector)
            box.clear()
            box.send_keys(query)
            if submit:
                box.send_keys(Keys.RETURN)
            time.sleep(2)
            return driver
        except Exception as e:
            print(f"Error performing search: {str(e)}")
            driver.quit()
            raise

    def get_text(self, selector, driver=None):
        print(f"[Browser] Getting text from selector: {selector}")
        if driver is None:
            driver = self.get_new_driver()
            driver.get(self.current_url)
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            text = element.text
            print(f"[Browser] Text found: {text[:200]}{'...' if len(text) > 200 else ''}")
            return text
        except Exception as e:
            print(f"Error getting text: {str(e)}")
            driver.quit()
            raise

    def screenshot(self, name_prefix="screenshot", driver=None):
        should_quit = False
        if driver is None:
            driver = self.get_new_driver()
            driver.get(self.current_url)
            should_quit = True
            
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name_prefix}_{ts}.png"
        driver.save_screenshot(filename)
        print(f"[Browser] Screenshot saved: {filename}")
        
        if should_quit:
            driver.quit()
        return filename

    def run_cli(self, command):
        print(f"[CLI] Running command in new terminal: {command}")
        try:
            # For macOS, use osascript to open a new terminal window
            apple_script = f'''
            tell application "Terminal"
                do script "{command}"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', apple_script])
            time.sleep(1)  # Give the command time to execute
            
            # Run the command in the background for capturing output
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(f"[CLI] Output:\n{result.stdout}")
            if result.stderr:
                print(f"[CLI] Error:\n{result.stderr}")
            return result.stdout, result.stderr
        except Exception as e:
            error_msg = f"Error running command: {str(e)}"
            print(f"[CLI] {error_msg}")
            return None, error_msg

    def call_api(self, method, url, **kwargs):
        print(f"[API] Calling {method.upper()} {url}")
        try:
            response = requests.request(method, url, **kwargs)
            print(f"[API] Status: {response.status_code}")
            print(f"[API] Response: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
            return response
        except Exception as e:
            print(f"[API] Error: {str(e)}")
            return None

    def run_runbook(self, runbook_path):
        print(f"[Runbook] Executing runbook: {runbook_path}")
        current_driver = None
        browser_opened = False
        try:
            with open(runbook_path, 'r') as f:
                lines = f.readlines()
            current_step = None
            for idx, line in enumerate(lines):
                line = line.strip('\n')
                if not line.strip():
                    continue
                if not line.startswith('ACTION:') and not line.startswith('    ACTION:') and not line.startswith(' '):
                    current_step = line.strip(':')
                    print(f"\n=== Step: {current_step} ===")
                    # Close browser at the end of a web step
                    if browser_opened and current_driver:
                        current_driver.quit()
                        current_driver = None
                        browser_opened = False
                    # Add sleep to allow demo viewers to see the step
                    time.sleep(2)
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
                            if not browser_opened:
                                current_driver = self.go_to(params['url'])
                                browser_opened = True
                            else:
                                current_driver.get(params['url'])
                                self.current_url = params['url']
                            time.sleep(2)
                        elif action == 'get_text':
                            text = self.get_text(params['selector'], current_driver)
                            print(f"[Runbook] Text from {params['selector']}:\n{text}\n")
                            time.sleep(2)
                        elif action == 'screenshot':
                            self.screenshot(params.get('name_prefix', 'screenshot'), current_driver)
                            time.sleep(2)
                        else:
                            if browser_opened and current_driver:
                                current_driver.quit()
                                current_driver = None
                                browser_opened = False
                            if action == 'cli':
                                self.run_cli(params['command'])
                                time.sleep(2)
                            elif action == 'api':
                                method = params.get('method', 'get')
                                url = params['url']
                                self.call_api(method, url)
                                time.sleep(2)
                    except Exception as e:
                        print(f"[ERROR] Failed to execute action '{action}' in step '{current_step}': {e}")
                        if browser_opened and current_driver:
                            current_driver.quit()
                            current_driver = None
                            browser_opened = False
        finally:
            if browser_opened and current_driver:
                current_driver.quit()

    def close(self):
        pass  # No need to close anything as we create new drivers for each action
