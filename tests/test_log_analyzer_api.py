import pytest
from fastapi.testclient import TestClient
from main import app # Your main FastAPI application
import io
import os
import shutil # For cleanup

# Create a TestClient instance
client = TestClient(app)

# For testing, we will let the app use its default "uploads" directory.
# We will perform cleanup after tests that create files there.
# A more robust solution would involve dependency injection for the UPLOADS_DIR
# or using a dedicated temporary directory managed by pytest fixtures.

# Ensure the default 'uploads' directory exists, as the app might rely on it.
# The log_analyzer_router.py creates "uploads" on startup.
# If tests run completely isolated without app startup, this might be needed.
# However, TestClient(app) typically initializes the app.
if not os.path.exists("uploads"):
    os.makedirs("uploads", exist_ok=True)


def test_log_analyzer_health():
    response = client.get("/log_analyzer/log_analyzer_health")
    assert response.status_code == 200
    assert response.json() == {"status": "Log Analyzer router is running"}

def test_analyze_log_upload_success():
    # Create a dummy CSV file in memory
    csv_content = "header1,header2\nvalue1,value2\nvalue3,value4"
    # Ensure the file is uniquely named to avoid conflicts if tests run in parallel or if cleanup fails
    test_filename = f"test_log_{os.urandom(4).hex()}.csv"
    
    csv_file_in_memory = io.BytesIO(csv_content.encode('utf-8'))
    
    # Store the path for cleanup
    test_file_path = os.path.join("uploads", test_filename)

    try:
        response = client.post(
            "/log_analyzer/analyze_log",
            files={"file": (test_filename, csv_file_in_memory, "text/csv")}
        )
        assert response.status_code == 200 # Endpoint returns 200 for successful task queuing
        json_response = response.json()
        assert json_response["message"] == "Log analysis started in background"
        assert json_response["filename"] == test_filename
        assert "analysis_id" in json_response

        # Check if the file was actually created in the "uploads" directory by the endpoint
        # This is an integration aspect of the test.
        assert os.path.exists(test_file_path), f"File {test_file_path} was not created by the endpoint."

    finally:
        # Cleanup: remove the test file created by the endpoint
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"Cleaned up test file: {test_file_path}")


def test_get_analysis_results_not_found():
    response = client.get("/log_analyzer/analyze_log/results/non_existent_id_12345")
    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis ID not found."}

# To test other states of get_analysis_results (processing, completed, failed),
# we would need to manipulate the `analysis_results_store` in `log_analyzer_router.py`
# or mock the background task. For this basic set, we focus on predictable states.

# Example of a fixture to clean up the uploads directory if it was created *only* for tests
# and if it were named differently (e.g., "uploads_test_temp").
# Since we are using the app's actual "uploads" dir, we clean up files individually.
# If a dedicated test uploads dir (e.g. UPLOADS_DIR_TEST from instructions) was used and
# the app was configured to use it during tests, then this kind of fixture would be useful.
# For now, direct cleanup in tests or a more targeted fixture is more appropriate.

# @pytest.fixture(scope="session", autouse=True)
# def cleanup_test_uploads_dir_fixture(request):
#     # This is an example if we used a dedicated test directory like UPLOADS_DIR_TEST
#     # and wanted to ensure it's cleaned up after all tests in a session.
#     # UPLOADS_DIR_TEST_SESSION = "uploads_test_temp_session"
#     # os.makedirs(UPLOADS_DIR_TEST_SESSION, exist_ok=True)
#     # # Here you would configure your app to use UPLOADS_DIR_TEST_SESSION
#     yield
#     # Teardown: remove the directory after tests are done
#     # if os.path.exists(UPLOADS_DIR_TEST_SESSION):
#     #     shutil.rmtree(UPLOADS_DIR_TEST_SESSION)
#     pass # Not actively using this pattern for now since we use the default 'uploads'

# Note: The `UPLOADS_DIR_TEST` variable from the instructions isn't used here because
# the application itself isn't configured to use a different upload directory during tests
# without more complex setup (like dependency injection for the path).
# The tests currently assume the default "uploads/" path and perform cleanup there.
