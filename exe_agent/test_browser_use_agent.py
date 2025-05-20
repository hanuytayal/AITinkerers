import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from exe_agent.browser_use_agent import BrowserUseAgent

class TestBrowserUseAgent(unittest.TestCase):

    def setUp(self):
        # Patch the webdriver.Chrome to prevent actual browser instances during tests
        self.patcher_driver = patch('exe_agent.browser_use_agent.webdriver.Chrome')
        self.mock_chrome = self.patcher_driver.start()
        
        # Import By and Keys here
        from selenium.webdriver.common.by import By
        self.By = By
        from selenium.webdriver.common.keys import Keys
        self.Keys = Keys

        self.mock_driver_instance = MagicMock()
        self.mock_chrome.return_value = self.mock_driver_instance # Ensure new drivers are this mock
        
        # Mock os.path.exists to prevent setup_browser_options from finding a real browser
        # This allows the real options object to be created and configured by setup_browser_options
        with patch('os.path.exists', return_value=False):
            self.agent = BrowserUseAgent(headless=True)
        # self.agent.options is now the real ChromeOptions object, configured by setup_browser_options

    def tearDown(self):
        self.patcher_driver.stop()

    def test_initialization(self):
        self.assertTrue(self.agent.headless)
        self.assertIsNotNone(self.agent.options)
        # ChromeOptions might initialize binary_location to '' if not found.
        self.assertIn(self.agent.options.binary_location, [None, ''])

    def test_get_new_driver(self):
        driver = self.agent.get_new_driver()
        self.mock_chrome.assert_called_once_with(options=self.agent.options)
        self.assertEqual(driver, self.mock_driver_instance)
        driver.implicitly_wait.assert_called_once_with(10)

    def test_go_to(self):
        test_url = "http://example.com"
        driver = self.agent.go_to(test_url)
        self.mock_driver_instance.get.assert_called_once_with(test_url)
        self.assertEqual(self.agent.current_url, test_url)
        self.assertEqual(driver, self.mock_driver_instance)

    def test_go_to_with_existing_driver(self):
        test_url = "http://example.com"
        mock_existing_driver = MagicMock()
        driver = self.agent.go_to(test_url, driver=mock_existing_driver)
        mock_existing_driver.get.assert_called_once_with(test_url)
        self.assertEqual(self.agent.current_url, test_url)
        self.assertEqual(driver, mock_existing_driver)
        self.mock_chrome.assert_not_called() # Should not create new driver

    def test_search(self):
        self.agent.current_url = "http://search.com"
        query = "test query"
        selector = "input[name='q']"
        mock_search_box = MagicMock()
        self.mock_driver_instance.find_element.return_value = mock_search_box
        
        driver = self.agent.search(query, selector)
        
        self.mock_driver_instance.get.assert_called_once_with("http://search.com")
        self.mock_driver_instance.find_element.assert_called_once_with(self.By.CSS_SELECTOR, selector) # Use self.By
        mock_search_box.clear.assert_called_once()
        mock_search_box.send_keys.assert_any_call(query)
        mock_search_box.send_keys.assert_any_call(self.Keys.RETURN) # Use self.Keys
        self.assertEqual(driver, self.mock_driver_instance)

    def test_get_text(self):
        self.agent.current_url = "http://textpage.com"
        selector = "div.content"
        expected_text = "This is the content."
        mock_element = MagicMock()
        mock_element.text = expected_text
        self.mock_driver_instance.find_element.return_value = mock_element

        text = self.agent.get_text(selector)

        self.mock_driver_instance.get.assert_called_once_with("http://textpage.com")
        self.mock_driver_instance.find_element.assert_called_once_with(self.By.CSS_SELECTOR, selector) # Use self.By
        self.assertEqual(text, expected_text)

    def test_screenshot(self):
        self.agent.current_url = "http://imagepage.com"
        name_prefix = "test_shot"
        
        with patch('exe_agent.browser_use_agent.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20230101_120000"
            expected_filename = "test_shot_20230101_120000.png"
            
            filename = self.agent.screenshot(name_prefix)
            
            self.mock_driver_instance.get.assert_called_once_with("http://imagepage.com")
            self.mock_driver_instance.save_screenshot.assert_called_once_with(expected_filename)
            self.assertEqual(filename, expected_filename)
            # Check if file was created (mocked, so it won't actually exist)
            # For a real test with file system, you might os.path.exists and cleanup

    @patch('exe_agent.browser_use_agent.subprocess.run')
    def test_run_cli(self, mock_subprocess_run):
        command = "ls -l"
        mock_subprocess_run.return_value = MagicMock(stdout="file1\nfile2", stderr="", returncode=0)
        
        stdout, stderr = self.agent.run_cli(command)
        
        # For macOS, osascript is called first
        if os.name == 'posix': # Simplified check, real check might be more specific
             mock_subprocess_run.assert_any_call(['osascript', '-e', unittest.mock.ANY])
        mock_subprocess_run.assert_any_call(command, shell=True, capture_output=True, text=True)
        self.assertEqual(stdout, "file1\nfile2")
        self.assertEqual(stderr, "")

    @patch('exe_agent.browser_use_agent.requests.request')
    def test_call_api(self, mock_requests_request):
        url = "http://api.example.com/data"
        method = "GET"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_requests_request.return_value = mock_response
        
        response = self.agent.call_api(method, url, headers={"X-Test": "true"})
        
        mock_requests_request.assert_called_once_with(method, url, headers={"X-Test": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '{"key": "value"}')

    @patch('builtins.open', new_callable=mock_open, read_data="Step1:\n ACTION: go_to url=\"http://test.com\"\nStep2:\n    ACTION: get_text selector=\"h1\"\n")
    @patch('exe_agent.browser_use_agent.time.sleep', MagicMock()) # Mock sleep to speed up test
    def test_run_runbook(self, mock_file):
        runbook_path = "dummy/path/to/runbook.txt"
        
        # Mocking specific actions
        self.agent.go_to = MagicMock(return_value=self.mock_driver_instance)
        self.agent.get_text = MagicMock(return_value="Mocked Text")
        
        self.agent.run_runbook(runbook_path)
        
        mock_file.assert_called_once_with(runbook_path, 'r')
        self.agent.go_to.assert_called_once_with("http://test.com") # Corrected: positional argument
        # Corrected: get_text is called with "h1" and None (driver is reset between steps)
        self.agent.get_text.assert_called_once_with("h1", None)
        # self.mock_driver_instance.quit.assert_called() # This will be called twice if go_to and get_text are in diff steps
        # current_driver.quit() is called at the start of "Step2" and at the end in finally.
        # Let's check the number of calls to quit on the driver instance that was returned by go_to
        # The driver from go_to is quit at the start of Step2.
        # If get_text created a new driver, that would be quit in the finally block.
        # Since get_text is mocked, it doesn't create a new driver.
        # So, the original mock_driver_instance (from go_to) should be quit once.
        self.mock_driver_instance.quit.assert_called_once()


    def test_close(self):
        # Close method is currently a pass, so just call it for coverage
        self.agent.close()
        # No assertions needed as it does nothing

if __name__ == '__main__':
    unittest.main()
