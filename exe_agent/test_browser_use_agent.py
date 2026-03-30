"""
Unit tests for the BrowserUseAgent class.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import requests # Import requests

# Import By and Keys at the top level
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
# Import custom exceptions and the main class
from exe_agent.browser_use_agent import (
    BrowserUseAgent,
    CLICommandError,
    RunbookError,
    NavigationError,
    SearchError,
    TextExtractionError,
    ScreenshotError,
    WebDriverSetupError,
    BrowserUseAgentError
)


class TestBrowserUseAgent(unittest.TestCase):
    """
    Test suite for the BrowserUseAgent class.
    Mocks external dependencies like Selenium WebDriver, requests, and subprocess.
    """

    def setUp(self):
        """
        Set up test environment before each test.
        Patches webdriver.Chrome and os.path.exists.
        Initializes a BrowserUseAgent instance.
        """
        self.patcher_chrome = patch('exe_agent.browser_use_agent.webdriver.Chrome')
        self.mock_chrome_class = self.patcher_chrome.start()

        self.mock_driver_instance = MagicMock()
        self.mock_driver_instance.title = "Mock Page Title"
        self.mock_chrome_class.return_value = self.mock_driver_instance

        self.by = By
        self.keys = Keys

        self.patcher_os_path = patch('os.path.exists', return_value=False)
        self.mock_os_path_exists = self.patcher_os_path.start()

        self.agent = BrowserUseAgent(headless=True)

    def tearDown(self):
        """Clean up test environment after each test."""
        self.patcher_chrome.stop()
        self.patcher_os_path.stop()
        if self.agent and self.agent.driver: # Ensure instance driver is closed
            self.agent.close()


    def test_initialization(self):
        """Test agent initialization and default settings."""
        self.assertTrue(self.agent.headless)
        self.assertIsNotNone(self.agent.options)
        self.assertIsNone(self.agent.driver, "Instance driver should be None initially")
        self.assertIn(self.agent.options.binary_location, [None, ''],
                      "Binary location should be None or empty if not found")
        self.mock_os_path_exists.assert_called()


    @patch('exe_agent.browser_use_agent.webdriver.Chrome')
    def test_get_new_driver_failure_first_attempt(self, mock_chrome_local):
        """Test get_new_driver failure on the first attempt, success on second."""
        mock_driver_instance_retry = MagicMock()
        mock_chrome_local.side_effect = [
            WebDriverSetupError("Initial fail"), # First call in get_new_driver
            mock_driver_instance_retry # Second call in get_new_driver (fallback)
        ]
        # self.agent.options will be passed to the mock_chrome_local
        driver = self.agent.get_new_driver()
        self.assertEqual(driver, mock_driver_instance_retry)
        self.assertEqual(mock_chrome_local.call_count, 2)


    @patch('exe_agent.browser_use_agent.webdriver.Chrome')
    def test_get_new_driver_failure_all_attempts(self, mock_chrome_local):
        """Test get_new_driver failure on all attempts."""
        mock_chrome_local.side_effect = WebDriverSetupError("Failed to init")
        with self.assertRaises(WebDriverSetupError):
            self.agent.get_new_driver()

    def test_get_new_driver(self):
        """Test creation of a new WebDriver instance via get_new_driver."""
        self.mock_chrome_class.reset_mock() # Reset from setUp
        self.mock_chrome_class.return_value = self.mock_driver_instance

        driver = self.agent.get_new_driver()
        self.mock_chrome_class.assert_called_once_with(options=self.agent.options)
        self.assertEqual(driver, self.mock_driver_instance)
        driver.implicitly_wait.assert_called_once_with(10)


    def test_go_to_instance_driver(self):
        """Test go_to method using and setting the instance driver."""
        test_url = "http://example.com"
        returned_driver = self.agent.go_to(test_url) # Should use/create self.driver

        self.assertEqual(returned_driver, self.mock_driver_instance)
        self.assertEqual(self.agent.driver, self.mock_driver_instance)
        self.mock_driver_instance.get.assert_called_once_with(test_url)
        self.assertEqual(self.agent.current_url, test_url)

    def test_go_to_with_provided_driver(self):
        """Test go_to method with a provided external driver."""
        test_url = "http://example.com/external"
        mock_external_driver = MagicMock()
        mock_external_driver.title = "External Driver Page" # For _is_driver_active

        returned_driver = self.agent.go_to(test_url, driver=mock_external_driver)

        self.assertEqual(returned_driver, mock_external_driver)
        mock_external_driver.get.assert_called_once_with(test_url)
        self.assertIsNone(self.agent.current_url,
                          "Agent's current_url should not change with external driver")
        self.assertIsNone(self.agent.driver,
                          "Agent's driver should not be set by external driver")

    @patch.object(BrowserUseAgent, '_is_driver_active', return_value=True)
    def test_search_instance_driver_active(self, mock_is_active):
        """Test search method with an active instance driver."""
        self.agent.current_url = "http://search.com"
        self.agent.driver = self.mock_driver_instance # Assume driver is active

        query = "test query"
        selector = "input[name='q']"
        mock_search_box = MagicMock()
        self.mock_driver_instance.find_element.return_value = mock_search_box

        returned_driver = self.agent.search(query, selector)

        self.mock_driver_instance.find_element.assert_called_once_with(self.by.CSS_SELECTOR, selector)
        mock_search_box.clear.assert_called_once()
        mock_search_box.send_keys.assert_any_call(query)
        mock_search_box.send_keys.assert_any_call(self.keys.RETURN)
        self.assertEqual(returned_driver, self.mock_driver_instance)
        mock_is_active.assert_called_with(self.mock_driver_instance)


    @patch.object(BrowserUseAgent, '_is_driver_active', side_effect=[False, True, True])
    def test_search_instance_driver_needs_load(self, mock_is_active):
        """Test search when instance driver needs to load current_url."""
        self.agent.current_url = "http://search.com"
        # self.agent.driver is initially None, _get_instance_driver will create it.
        # self.mock_driver_instance will be assigned to self.agent.driver.

        mock_search_box = MagicMock()
        self.mock_driver_instance.find_element.return_value = mock_search_box

        self.agent.search("query", "selector")

        # get_new_driver was called by _get_instance_driver
        self.mock_chrome_class.assert_called_once()
        # go_to was called because _is_driver_active returned False first
        self.mock_driver_instance.get.assert_called_once_with("http://search.com")
        mock_is_active.assert_any_call(self.mock_driver_instance)


    @patch.object(BrowserUseAgent, '_is_driver_active', return_value=True)
    def test_get_text_instance_driver_active(self, mock_is_active):
        """Test get_text method with an active instance driver."""
        self.agent.current_url = "http://textpage.com"
        self.agent.driver = self.mock_driver_instance

        selector = "div.content"
        expected_text = "This is the content."
        mock_element = MagicMock()
        mock_element.text = expected_text
        self.mock_driver_instance.find_element.return_value = mock_element

        text = self.agent.get_text(selector)

        self.mock_driver_instance.find_element.assert_called_once_with(self.by.CSS_SELECTOR, selector)
        self.assertEqual(text, expected_text)
        mock_is_active.assert_called_with(self.mock_driver_instance)


    @patch.object(BrowserUseAgent, '_is_driver_active', return_value=True)
    def test_screenshot_instance_driver_active(self, mock_is_active):
        """Test screenshot method with an active instance driver."""
        self.agent.current_url = "http://imagepage.com"
        self.agent.driver = self.mock_driver_instance
        name_prefix = "test_shot"

        with patch('exe_agent.browser_use_agent.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20230101_120000"
            expected_filename = "test_shot_20230101_120000.png"
            filename = self.agent.screenshot(name_prefix)
            self.mock_driver_instance.save_screenshot.assert_called_once_with(expected_filename)
            self.assertEqual(filename, expected_filename)
        mock_is_active.assert_called_with(self.mock_driver_instance)


    @patch('exe_agent.browser_use_agent.subprocess.run')
    def test_run_cli_success(self, mock_subprocess_run):
        """Test successful CLI command execution."""
        command = "ls -l"
        # Mock for the background command capture part
        mock_result = MagicMock(stdout="file1\nfile2", stderr="", returncode=0)

        # If osascript is expected (macOS), handle its mock call too
        if sys.platform == 'darwin':
            mock_subprocess_run.side_effect = [MagicMock(), mock_result] # First for osascript, second for actual
        else:
            mock_subprocess_run.return_value = mock_result

        stdout, stderr = self.agent.run_cli(command)

        # Check the background command execution call
        actual_command_call = None
        for call_obj in mock_subprocess_run.call_args_list:
            if call_obj.args[0] == command:
                actual_command_call = call_obj
                break
        self.assertIsNotNone(actual_command_call, "Background command was not executed")
        self.assertEqual(actual_command_call.kwargs['shell'], True)
        self.assertEqual(actual_command_call.kwargs['capture_output'], True)
        self.assertEqual(actual_command_call.kwargs['text'], True)
        self.assertEqual(actual_command_call.kwargs['timeout'], 300)
        self.assertEqual(actual_command_call.kwargs['check'], False)

        self.assertEqual(stdout, "file1\nfile2")
        self.assertEqual(stderr, "")


    @patch('exe_agent.browser_use_agent.subprocess.run')
    def test_run_cli_failure(self, mock_subprocess_run):
        """Test CLI command execution failure."""
        command = "badcommand"
        # Mock for the background command capture part
        mock_result = MagicMock(stdout="", stderr="error message", returncode=1)
        if sys.platform == 'darwin':
            mock_subprocess_run.side_effect = [MagicMock(), mock_result]
        else:
            mock_subprocess_run.return_value = mock_result

        with self.assertRaisesRegex(CLICommandError, "failed with return code 1.*error message"):
            self.agent.run_cli(command)


    @patch('exe_agent.browser_use_agent.requests.request')
    def test_call_api_success(self, mock_requests_request):
        """Test successful API call."""
        url = "http://api.example.com/data"
        method = "GET"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.raise_for_status = MagicMock()
        mock_requests_request.return_value = mock_response

        response = self.agent.call_api(method, url, headers={"X-Test": "true"})

        mock_requests_request.assert_called_once_with(
            method, url, headers={"X-Test": "true"}, timeout=10
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '{"key": "value"}')
        mock_response.raise_for_status.assert_called_once()

    @patch('exe_agent.browser_use_agent.requests.request')
    def test_call_api_failure(self, mock_requests_request):
        """Test API call failure (e.g., network error or HTTP error status)."""
        url = "http://api.example.com/error"
        method = "GET"
        # Simulate requests.exceptions.RequestException for network issues
        mock_requests_request.side_effect = requests.exceptions.RequestException("Network Error")
        with self.assertRaisesRegex(BrowserUseAgentError, "API call to GET http://api.example.com/error failed: Network Error"):
            self.agent.call_api(method, url)

        # Simulate HTTPError (e.g., 404 or 500)
        mock_response_error = MagicMock()
        mock_response_error.status_code = 404
        mock_response_error.text = 'Not Found'
        mock_response_error.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        mock_requests_request.return_value = mock_response_error
        mock_requests_request.side_effect = None # Reset side_effect

        with self.assertRaisesRegex(BrowserUseAgentError, "404 Client Error"):
            self.agent.call_api(method, url)


    @patch('builtins.open', new_callable=mock_open, read_data=(
        "Step1: First step\n"
        "  ACTION: go_to url=\"http://step1.com\"\n"
        "# This is a comment\n"
        "Step2: Second step\n"
        "    ACTION: get_text selector=\"h1\"\n"
    ))
    @patch('exe_agent.browser_use_agent.time.sleep', MagicMock())
    def test_run_runbook_success(self, mock_file_open):
        """Test successful execution of a runbook."""
        runbook_path = "dummy/path/to/runbook.txt"

        mock_driver_for_step1 = MagicMock(name="DriverForStep1")
        # Mock the internal action handlers
        self.agent._handle_go_to = MagicMock(return_value=mock_driver_for_step1)
        # _handle_get_text is called with the driver from the previous step,
        # but run_runbook quits it if a new step starts.
        self.agent._handle_get_text = MagicMock(return_value=None) # Driver passed to it will be None

        self.agent.run_runbook(runbook_path)

        mock_file_open.assert_called_once_with(runbook_path, 'r', encoding='utf-8')
        self.agent._handle_go_to.assert_called_once_with(
            {'url': 'http://step1.com'}, None
        )
        # Driver for _handle_get_text should be None as it's a new step
        self.agent._handle_get_text.assert_called_once_with(
            {'selector': 'h1'}, None
        )
        # The driver created in step 1 should be quit when "Step2" is encountered
        mock_driver_for_step1.quit.assert_called_once()


    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_run_runbook_file_not_found(self, mock_file_open):
        """Test runbook execution when the runbook file is not found."""
        with self.assertRaisesRegex(RunbookError, "Runbook file not found"):
            self.agent.run_runbook("nonexistent.txt")
        mock_file_open.assert_called_once_with("nonexistent.txt", 'r', encoding='utf-8')


    @patch('builtins.open', new_callable=mock_open, read_data="ACTION: unknown_action param=val")
    def test_run_runbook_unknown_action(self, mock_file_open):
        """Test runbook with an unknown action."""
        runbook_path = "dummy.txt"
        with self.assertRaisesRegex(RunbookError, "Unknown action 'unknown_action'"):
            self.agent.run_runbook(runbook_path)
        mock_file_open.assert_called_once_with(runbook_path, 'r', encoding='utf-8')


    def test_close_instance_driver(self):
        """Test closing the managed instance driver."""
        self.agent.driver = self.mock_driver_instance
        self.agent.current_url = "http://example.com" # Should be reset

        self.agent.close()

        self.mock_driver_instance.quit.assert_called_once()
        self.assertIsNone(self.agent.driver)
        self.assertIsNone(self.agent.current_url)


    def test_close_no_driver(self):
        """Test close method when no instance driver is active."""
        self.assertIsNone(self.agent.driver)
        self.agent.close() # Should not raise any error
        self.mock_driver_instance.quit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
