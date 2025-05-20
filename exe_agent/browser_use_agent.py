"""
BrowserUseAgent: An agent that can use a web browser to perform actions using Selenium,
execute CLI commands, and make API calls.
"""
import os
import subprocess
import time
from datetime import datetime

import requests
from selenium import webdriver
# Dynamically import By and Keys to avoid direct selenium dependency if not used.
# However, for clarity in a class that heavily uses Selenium, direct imports are fine.
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException


# --- Custom Exceptions ---
class BrowserUseAgentError(Exception):
    """Base exception for BrowserUseAgent errors."""

class WebDriverSetupError(BrowserUseAgentError):
    """Error during WebDriver setup."""

class NavigationError(BrowserUseAgentError):
    """Error during browser navigation."""

class SearchError(BrowserUseAgentError):
    """Error during a search operation."""

class TextExtractionError(BrowserUseAgentError):
    """Error during text extraction."""

class ScreenshotError(BrowserUseAgentError):
    """Error during screenshot capture."""

class CLICommandError(BrowserUseAgentError):
    """Error during CLI command execution."""

class RunbookError(BrowserUseAgentError):
    """Error during runbook execution."""


class BrowserUseAgent:
    """
    Automates browser actions, CLI commands, and API calls.
    Manages a single Selenium WebDriver instance for instance-level browser operations.
    Runbook execution manages its own driver lifecycle per step.
    """

    def __init__(self, headless=True):
        """
        Initializes the BrowserUseAgent.

        Args:
            headless (bool): If True, runs the browser in headless mode.
        """
        self.headless = headless
        self.options = self._setup_browser_options()
        self.driver = None  # Instance driver, lazily initialized
        self.current_url = None # Last known URL for the instance driver

    def _setup_browser_options(self):
        """
        Configures and returns ChromeOptions for the WebDriver.
        """
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        # Chrome/Chromium detection for macOS - kept for compatibility
        # Consider making this more generic or configurable if needed for other OS.
        chrome_candidates = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/opt/homebrew/bin/chrome', # For Homebrew on Apple Silicon/Intel
            '/opt/homebrew/bin/chromium',
        ]
        browser_path = None
        for path in chrome_candidates:
            if os.path.exists(path):
                browser_path = path
                break
        if browser_path:
            options.binary_location = browser_path
        return options

    def get_new_driver(self):
        """
        Creates and returns a new Selenium WebDriver instance.
        Attempts to use selenium-manager if direct instantiation fails.

        Returns:
            webdriver.Chrome: A new WebDriver instance.

        Raises:
            WebDriverSetupError: If driver initialization fails after retries.
        """
        try:
            # First attempt: direct instantiation
            driver = webdriver.Chrome(options=self.options)
            driver.implicitly_wait(10) # Default wait for elements
            return driver
        except WebDriverException as e:
            print(f"Error initializing Chrome driver directly: {e}")
            print("Trying to initialize WebDriver using selenium-manager (built-in fallback)...")
            # Second attempt: rely on selenium-manager (often the default behavior now)
            # Re-instantiating Chrome without service_log_path to let Selenium handle it.
            try:
                driver = webdriver.Chrome(options=self.options)
                driver.implicitly_wait(10)
                return driver
            except WebDriverException as e2:
                raise WebDriverSetupError(
                    f"Failed to initialize Chrome driver after fallback: {e2}"
                ) from e2

    def _get_instance_driver(self):
        """
        Returns the managed instance driver, creating it if it doesn't exist.
        """
        if self.driver is None or not self._is_driver_active(self.driver):
            self.driver = self.get_new_driver()
        return self.driver

    @staticmethod
    def _is_driver_active(driver):
        """Checks if the driver session is active."""
        try:
            # Accessing a property like title will raise an error if session is not active
            # pylint: disable=pointless-statement
            driver.title
            return True
        except WebDriverException:
            return False

    def go_to(self, url, driver=None):
        """
        Navigates to the given URL.

        Args:
            url (str): The URL to navigate to.
            driver (webdriver.Chrome, optional): An existing WebDriver to use.
                If None, uses the managed instance driver.

        Returns:
            webdriver.Chrome: The WebDriver instance used for navigation.

        Raises:
            NavigationError: If navigation fails.
        """
        print(f"[Browser] Navigating to: {url}")
        active_driver = driver or self._get_instance_driver()
        try:
            active_driver.get(url)
            if active_driver == self.driver: # Only update current_url for the instance driver
                self.current_url = url
            time.sleep(2)  # Consider making sleep configurable or using explicit waits
            return active_driver
        except TimeoutException as e:
            msg = f"Timeout navigating to {url}: {e}"
            print(f"[ERROR] {msg}")
            if driver is None and active_driver == self.driver: # only quit instance driver if it was used
                self.close()
            raise NavigationError(msg) from e
        except WebDriverException as e:
            msg = f"Error navigating to {url}: {e}"
            print(f"[ERROR] {msg}")
            if driver is None and active_driver == self.driver:
                self.close()
            raise NavigationError(msg) from e

    def search(self, query, search_box_selector, submit=True, driver=None):
        """
        Performs a search on the current page of the given driver or instance driver.

        Args:
            query (str): The search query.
            search_box_selector (str): CSS selector for the search input box.
            submit (bool): If True, submits the search (e.g., presses Enter).
            driver (webdriver.Chrome, optional): An existing WebDriver to use.
                If None, uses the managed instance driver. The driver must be on a page.

        Returns:
            webdriver.Chrome: The WebDriver instance used.

        Raises:
            SearchError: If the search fails.
            NavigationError: If self.current_url is not set and new driver is created.
        """
        print(f"[Browser] Searching for '{query}' in selector '{search_box_selector}'")
        active_driver = driver or self._get_instance_driver()

        # If using instance driver and it's fresh, it might need current_url
        if active_driver == self.driver and not self._is_driver_active(active_driver):
            if not self.current_url:
                raise SearchError("Cannot search: instance driver is not on a page (current_url is None).")
            self.go_to(self.current_url, driver=active_driver) # Reload or ensure page
        elif driver and not self._is_driver_active(active_driver): # Passed driver but inactive
            raise SearchError("Cannot search: provided driver is not active or on a page.")


        try:
            box = active_driver.find_element(By.CSS_SELECTOR, search_box_selector)
            box.clear()
            box.send_keys(query)
            if submit:
                box.send_keys(Keys.RETURN)
            time.sleep(2) # Consider explicit waits
            return active_driver
        except (NoSuchElementException, WebDriverException) as e:
            msg = f"Error performing search: {e}"
            print(f"[ERROR] {msg}")
            if driver is None and active_driver == self.driver: # only quit instance driver
                 self.close()
            raise SearchError(msg) from e

    def get_text(self, selector, driver=None):
        """
        Extracts text from an element on the current page of the given driver or instance driver.

        Args:
            selector (str): CSS selector for the element.
            driver (webdriver.Chrome, optional): An existing WebDriver to use.
                If None, uses the managed instance driver.

        Returns:
            str: The extracted text.

        Raises:
            TextExtractionError: If text extraction fails.
            NavigationError: If self.current_url is not set and new driver is created.
        """
        print(f"[Browser] Getting text from selector: {selector}")
        active_driver = driver or self._get_instance_driver()

        if active_driver == self.driver and not self._is_driver_active(active_driver):
            if not self.current_url:
                raise TextExtractionError("Cannot get text: instance driver not on a page (current_url is None).")
            self.go_to(self.current_url, driver=active_driver)
        elif driver and not self._is_driver_active(active_driver):
            raise TextExtractionError("Cannot get text: provided driver is not active or on a page.")

        try:
            element = active_driver.find_element(By.CSS_SELECTOR, selector)
            text = element.text
            print(f"[Browser] Text found: {text[:200]}{'...' if len(text) > 200 else ''}")
            return text
        except (NoSuchElementException, WebDriverException) as e:
            msg = f"Error getting text using selector '{selector}': {e}"
            print(f"[ERROR] {msg}")
            if driver is None and active_driver == self.driver:
                self.close()
            raise TextExtractionError(msg) from e

    def screenshot(self, name_prefix="screenshot", driver=None):
        """
        Takes a screenshot of the current page.

        Args:
            name_prefix (str): Prefix for the screenshot filename.
            driver (webdriver.Chrome, optional): An existing WebDriver to use.
                If None, uses the managed instance driver.

        Returns:
            str: The filename of the saved screenshot.

        Raises:
            ScreenshotError: If screenshot capture fails.
            NavigationError: If self.current_url is not set and new driver is created.
        """
        active_driver = driver or self._get_instance_driver()
        is_temp_driver_session = (driver is None) # True if we are using self.driver

        if active_driver == self.driver and not self._is_driver_active(active_driver):
            if not self.current_url:
                raise ScreenshotError("Cannot take screenshot: instance driver not on a page (current_url is None).")
            self.go_to(self.current_url, driver=active_driver) # Ensure page is loaded
        elif driver and not self._is_driver_active(active_driver):
            raise ScreenshotError("Cannot take screenshot: provided driver is not active or on a page.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name_prefix}_{timestamp}.png"
        try:
            active_driver.save_screenshot(filename)
            print(f"[Browser] Screenshot saved: {filename}")
            return filename
        except WebDriverException as e:
            msg = f"Error taking screenshot: {e}"
            print(f"[ERROR] {msg}")
            if is_temp_driver_session and active_driver == self.driver : # only close instance driver
                self.close()
            raise ScreenshotError(msg) from e

    def run_cli(self, command):
        """
        Runs a CLI command. On macOS, it attempts to run in a new Terminal window
        and also captures output in the background. On other OS, it runs in the background.
        Note: The new terminal window on macOS is for interactive visibility; output is
        captured from the background execution. `timeout` for subprocess.run is for the
        command itself, not for the osascript part.

        Args:
            command (str): The command to run.

        Returns:
            tuple: (stdout, stderr) from the background execution.

        Raises:
            CLICommandError: If the command fails or an error occurs.
        """
        print(f"[CLI] Running command: {command}")
        try:
            if os.name == 'posix': # More specific check for macOS could be sys.platform == 'darwin'
                try:
                    # Attempt to open in new terminal for visibility (macOS specific)
                    escaped_command = command.replace('"', '\\"')
                    apple_script = f'''
                    tell application "Terminal"
                        do script "{escaped_command}"
                        activate
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', apple_script], timeout=5, check=False)
                    time.sleep(1)  # Brief pause for terminal to open
                except FileNotFoundError: # osascript not found
                    print("[CLI] osascript not found, cannot open in new Terminal. Running in background only.")
                except subprocess.TimeoutExpired:
                    print("[CLI] osascript timed out. Command likely still running in new terminal if opened.")
                except Exception as e_script: # Catch other osascript errors
                    print(f"[CLI] Error with osascript: {e_script}. Running in background only.")

            # Run command in background to capture output
            # Using check=False to manually inspect result
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300, check=False)

            print(f"[CLI] STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"[CLI] STDERR:\n{result.stderr}")

            if result.returncode != 0:
                raise CLICommandError(
                    f"Command '{command}' failed with return code {result.returncode}\n"
                    f"Stderr: {result.stderr}"
                )
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            raise CLICommandError(f"Command '{command}' timed out.") from e
        except Exception as e: # Catch other errors like issues with subprocess.run itself
            raise CLICommandError(f"Error running command '{command}': {e}") from e

    def call_api(self, method, url, **kwargs):
        """
        Makes an API call.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            url (str): API endpoint URL.
            **kwargs: Additional arguments for requests.request (e.g., json, headers).

        Returns:
            requests.Response: The API response object.

        Raises:
            BrowserUseAgentError: If the API call fails.
        """
        print(f"[API] Calling {method.upper()} {url}")
        try:
            # Ensure a timeout is set, default to 10 seconds if not provided
            kwargs.setdefault('timeout', 10)
            response = requests.request(method, url, **kwargs)
            print(f"[API] Status: {response.status_code}")
            print(f"[API] Response: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response
        except requests.exceptions.RequestException as e:
            msg = f"API call to {method.upper()} {url} failed: {e}"
            print(f"[API] Error: {msg}")
            raise BrowserUseAgentError(msg) from e

    # --- Runbook Execution ---

    def _parse_action_line(self, action_line):
        """Parses an ACTION line from the runbook."""
        parts = action_line.split()
        action = parts[0]
        params = {}
        for p_part in parts[1:]:
            if '=' in p_part:
                key, value = p_part.split('=', 1)
                # Remove quotes around value if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                params[key] = value
        return action, params

    def _handle_go_to(self, params, current_driver):
        url = params.get('url')
        if not url:
            raise RunbookError("go_to action missing 'url' parameter.")
        new_driver = self.go_to(url, driver=current_driver)
        # Update current_url for the main instance if this go_to used/updated the instance driver
        if new_driver == self.driver:
            self.current_url = url
        return new_driver # Return the driver used or created

    def _handle_search(self, params, current_driver):
        query = params.get('query')
        selector = params.get('selector')
        if not query or not selector:
            raise RunbookError("search action missing 'query' or 'selector'.")
        submit = params.get('submit', 'true').lower() == 'true'
        # search method will use current_driver or create one if None
        self.search(query, selector, submit=submit, driver=current_driver)
        return current_driver # search doesn't typically change the driver instance

    def _handle_get_text(self, params, current_driver):
        selector = params.get('selector')
        if not selector:
            raise RunbookError("get_text action missing 'selector'.")
        text = self.get_text(selector, driver=current_driver)
        print(f"[Runbook] Text from {selector}:\n{text}\n")
        return current_driver

    def _handle_screenshot(self, params, current_driver):
        name_prefix = params.get('name_prefix', 'runbook_screenshot')
        self.screenshot(name_prefix, driver=current_driver)
        return current_driver

    def _handle_cli(self, params, current_driver): # pylint: disable=unused-argument
        command = params.get('command')
        if not command:
            raise RunbookError("cli action missing 'command'.")
        self.run_cli(command)
        return current_driver # CLI does not affect browser driver

    def _handle_api(self, params, current_driver): # pylint: disable=unused-argument
        method = params.get('method', 'get')
        url = params.get('url')
        if not url:
            raise RunbookError("api action missing 'url'.")
        # For simplicity, not parsing complex kwargs for API from runbook here.
        # Could extend to support headers, json body from params if needed.
        self.call_api(method, url)
        return current_driver # API does not affect browser driver

    def run_runbook(self, runbook_path):
        """
        Executes a series of actions defined in a runbook text file.
        Manages a WebDriver instance specifically for the duration of this runbook execution,
        potentially closing and reopening it between steps.

        Args:
            runbook_path (str): Path to the runbook file.

        Raises:
            RunbookError: If there's an error reading or executing the runbook.
        """
        print(f"[Runbook] Executing runbook: {runbook_path}")

        action_handlers = {
            'go_to': self._handle_go_to,
            'search': self._handle_search,
            'get_text': self._handle_get_text,
            'screenshot': self._handle_screenshot,
            'cli': self._handle_cli,
            'api': self._handle_api,
        }

        current_runbook_driver = None # Driver for this specific runbook execution
        current_step_label = None

        try:
            with open(runbook_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise RunbookError(f"Runbook file not found: {runbook_path}") from None
        except IOError as e:
            raise RunbookError(f"Error reading runbook file {runbook_path}: {e}") from e

        try:
            for line_num, raw_line in enumerate(lines, 1):
                line = raw_line.strip()
                if not line or line.startswith('#'): # Skip empty lines and comments
                    continue

                if not line.startswith('ACTION:') and \
                   not line.startswith('    ACTION:') and \
                   not line.startswith('  ACTION:'): # Allow some indentation for ACTION
                    # This line defines a new "Step"
                    current_step_label = line.strip(':')
                    print(f"\n=== Step: {current_step_label} ===")
                    time.sleep(0.5) # Reduced sleep

                    # Close driver at the start of a new logical step from the runbook
                    if current_runbook_driver:
                        print("[Runbook] Closing driver at the start of new step.")
                        current_runbook_driver.quit()
                        current_runbook_driver = None
                elif 'ACTION:' in line:
                    action_keyword_pos = line.find('ACTION:')
                    action_line_str = line[action_keyword_pos + len('ACTION:'):].strip()
                    try:
                        action_name, params = self._parse_action_line(action_line_str)
                    except Exception as e_parse: # pylint: disable=broad-except
                        msg = f"Error parsing action line {line_num} ('{line}'): {e_parse}"
                        print(f"[ERROR] {msg}")
                        raise RunbookError(msg) from e_parse

                    if action_name in action_handlers:
                        print(f"[Runbook] Executing: {action_name} with params {params}")
                        try:
                            # Handler updates current_runbook_driver (e.g. go_to creates it)
                            current_runbook_driver = action_handlers[action_name](
                                params, current_runbook_driver
                            )
                            time.sleep(0.5) # Reduced sleep after action
                        except BrowserUseAgentError as e_action: # Catch specific agent errors
                            msg = (f"Error in action '{action_name}' (step: {current_step_label}, "
                                   f"line: {line_num}): {e_action}")
                            print(f"[ERROR] {msg}")
                            # Decide if runbook should stop or continue on action error
                            # For now, let it propagate, effectively stopping.
                            raise RunbookError(msg) from e_action
                        except Exception as e_generic: # Catch unexpected errors during action
                            msg = (f"Unexpected error in action '{action_name}' "
                                   f"(step: {current_step_label}, line: {line_num}): {e_generic}")
                            print(f"[ERROR] {msg}")
                            raise RunbookError(msg) from e_generic
                    else:
                        msg = f"Unknown action '{action_name}' in runbook at line {line_num}."
                        print(f"[ERROR] {msg}")
                        # Optionally, decide to skip unknown actions or raise error
                        # For now, raise an error.
                        raise RunbookError(msg)
                else:
                    # Lines that are not comments, not empty, not step labels, not actions.
                    print(f"[Runbook] Warning: Ignoring malformed line {line_num}: '{line}'")

        finally:
            if current_runbook_driver:
                print("[Runbook] Ensuring runbook driver is closed at the end.")
                current_runbook_driver.quit()

    def close(self):
        """
        Closes the managed Selenium WebDriver instance, if active.
        """
        if self.driver:
            try:
                print("[Browser] Closing instance WebDriver.")
                self.driver.quit()
            except WebDriverException as e:
                print(f"Error quitting instance WebDriver: {e}")
            finally:
                self.driver = None
                self.current_url = None
