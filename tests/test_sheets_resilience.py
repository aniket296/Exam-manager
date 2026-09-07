"""
Suite 3: Google Sheets Resilience & Rate Limiting (Unit & Integration Tests)
Focus: Mock HTTP 429 Resource Exhausted / Quota Exceeded, exponential backoff retries, and data preservation.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from backend.utils.retry import retry_with_backoff
from tests.fixtures.mock_sheets import MockGSpreadAPIError, MockSpreadsheet, MockWorksheet
from backend.services.sheets_service import GoogleSheetsService

# --- 1. Custom Exponential Backoff Unit Tests ---
def test_exponential_backoff_retry_behavior():
    call_attempts = 0

    @retry_with_backoff(retries=5, initial_delay=0.01, backoff_factor=1.5, exceptions=(MockGSpreadAPIError,))
    def flaky_google_api(success_after_attempt=3):
        nonlocal call_attempts
        call_attempts += 1
        if call_attempts < success_after_attempt:
            raise MockGSpreadAPIError("429 Too Many Requests: Rate Limit Exceeded", code=429)
        return {"status": "SUCCESS", "records_written": 1}

    # Clears on attempt 3 -> Must succeed
    result = flaky_google_api(success_after_attempt=3)
    assert result["status"] == "SUCCESS"
    assert call_attempts == 3

def test_exponential_backoff_fails_after_max_retries():
    call_attempts = 0

    @retry_with_backoff(retries=5, initial_delay=0.01, backoff_factor=1.2, exceptions=(MockGSpreadAPIError,))
    def always_exhausted_api():
        nonlocal call_attempts
        call_attempts += 1
        raise MockGSpreadAPIError("429 Persistent Quota Exhaustion", code=429)

    # Exceeds max 5 retries -> Must raise error without dropping unhandled exceptions
    with pytest.raises(MockGSpreadAPIError) as exc_info:
        always_exhausted_api()

    assert exc_info.value.code == 429
    assert call_attempts == 5

# --- 2. GoogleSheetsService Eventual Consistency & Resilience Test ---
def test_sheets_service_eventual_success_without_data_loss():
    # Simulate API quota clearing on attempt 2
    mock_ss = MockSpreadsheet(fail_count=2)
    service = GoogleSheetsService()
    service.is_configured = True
    service.spreadsheet = mock_ss

    attempt_record = {
        "AttemptID": "att_resilience_99",
        "OrderID": "ord_99",
        "PaymentID": "pay_99",
        "Name": "Karan Malhotra",
        "StudentIdentifier": "Class 7",
        "PaperID": "pap_resilience",
        "PaperVersion": 1,
        "AmountMinorUnits": 5000,
        "Currency": "INR",
        "Status": "COMPLETED",
        "Score": 18.0
    }

    # sync_attempt has @retry_with_backoff
    service.sync_attempt(attempt_record)

    # Assert row was successfully written after clearing 429 quota retries
    ws = mock_ss.worksheet("Attempts")
    assert len(ws.rows) == 1
    saved_row = ws.rows[0]
    assert saved_row[0] == "att_resilience_99"
    assert saved_row[3] == "Karan Malhotra"
    assert saved_row[17] == "18.0"
    # Assert it retried through the failures
    assert ws.call_count >= 3

