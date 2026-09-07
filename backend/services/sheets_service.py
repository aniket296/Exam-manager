import json
import logging
import os
from typing import Optional, Dict, Any, List
from backend.config import settings
from backend.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """
    Service to manage communication with Google Sheets using gspread.
    Includes exponential backoff, batch syncing, and fallback handling.
    """
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.is_configured = False
        self._init_client()

    def _init_client(self):
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            service_account_info = None
            if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
                try:
                    service_account_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
                except Exception as e:
                    logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

            elif settings.GOOGLE_SERVICE_ACCOUNT_PATH and os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_PATH):
                with open(settings.GOOGLE_SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
                    service_account_info = json.load(f)

            if service_account_info and settings.GOOGLE_SHEET_ID:
                creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
                self.client = gspread.authorize(creds)
                self.spreadsheet = self.client.open_by_key(settings.GOOGLE_SHEET_ID)
                self.is_configured = True
                self._ensure_worksheets()
                logger.info("Successfully connected to Google Sheets.")
            else:
                logger.info("Google Sheets not fully configured. Operating in local storage mode.")
        except Exception as e:
            logger.warning(f"Google Sheets initialization skipped or failed: {e}. Using local store.")
            self.is_configured = False

    def _ensure_worksheets(self):
        """Ensures Papers, Attempts, and WebhookEvents worksheets exist with proper column headers."""
        if not self.spreadsheet:
            return

        sheet_headers = {
            "Papers": [
                "PaperID", "Title", "PriceMinorUnits", "Currency", "TimeLimitMinutes",
                "Status", "Version", "NegativeMarkingEnabled", "ShowAnswerKey",
                "AllowResume", "AntiCheatPolicy", "QuestionsJSON", "CreatedAt", "UpdatedAt"
            ],
            "Attempts": [
                "AttemptID", "OrderID", "PaymentID", "Name", "StudentIdentifier",
                "PhoneOrContact", "PaperID", "PaperVersion", "AmountMinorUnits",
                "Currency", "Status", "AttemptTokenHash", "TokenCreatedAt",
                "TokenExpiresAt", "StartedAt", "Deadline", "CompletedAt", "Score",
                "StrikeCount", "SessionID", "LastSeenAt", "QuestionOrderJSON",
                "OptionOrderJSON", "SubmissionHash", "Timestamp"
            ],
            "WebhookEvents": [
                "EventID", "EventType", "OrderID", "PaymentID", "ReceivedAt",
                "ProcessedAt", "ProcessingStatus", "ErrorMessage"
            ]
        }

        existing_sheets = [ws.title for ws in self.spreadsheet.worksheets()]
        for title, headers in sheet_headers.items():
            try:
                if title not in existing_sheets:
                    ws = self.spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
                    ws.append_row(headers)
                else:
                    ws = self.spreadsheet.worksheet(title)
                    existing_row1 = ws.row_values(1)
                    if not existing_row1:
                        ws.append_row(headers)
            except Exception as e:
                logger.warning(f"Error ensuring worksheet {title}: {e}")

    @retry_with_backoff(retries=3, initial_delay=0.1)
    def sync_paper(self, paper_dict: Dict[str, Any]):
        """Upserts a paper row into the Papers worksheet with retries."""
        if not self.is_configured or not self.spreadsheet:
            return
        ws = self.spreadsheet.worksheet("Papers")
        paper_id = str(paper_dict.get("PaperID", ""))
        
        q_json = paper_dict.get("QuestionsJSON", "[]")
        if isinstance(q_json, (dict, list)):
            q_json = json.dumps(q_json)

        row = [
            paper_id,
            str(paper_dict.get("Title", "")),
            str(paper_dict.get("PriceMinorUnits", 0)),
            str(paper_dict.get("Currency", "INR")),
            str(paper_dict.get("TimeLimitMinutes", 30)),
            str(paper_dict.get("Status", "DRAFT")),
            str(paper_dict.get("Version", 1)),
            str(paper_dict.get("NegativeMarkingEnabled", False)),
            str(paper_dict.get("ShowAnswerKey", False)),
            str(paper_dict.get("AllowResume", True)),
            str(paper_dict.get("AntiCheatPolicy", "AUTO_SUBMIT_ON_3")),
            q_json,
            str(paper_dict.get("CreatedAt", "")),
            str(paper_dict.get("UpdatedAt", ""))
        ]

        cell = ws.find(paper_id)
        if cell:
            ws.update(values=[row], range_name=f"A{cell.row}:N{cell.row}")
        else:
            ws.append_row(row)

    @retry_with_backoff(retries=3, initial_delay=0.1)
    def sync_attempt(self, attempt_dict: Dict[str, Any]):
        """Upserts an attempt row into the Attempts worksheet with retries."""
        if not self.is_configured or not self.spreadsheet:
            return
        ws = self.spreadsheet.worksheet("Attempts")
        attempt_id = str(attempt_dict.get("AttemptID", ""))
        row = [
            attempt_id,
            str(attempt_dict.get("OrderID", "")),
            str(attempt_dict.get("PaymentID", "")),
            str(attempt_dict.get("Name", "")),
            str(attempt_dict.get("StudentIdentifier", "")),
            str(attempt_dict.get("PhoneOrContact", "")),
            str(attempt_dict.get("PaperID", "")),
            str(attempt_dict.get("PaperVersion", "")),
            str(attempt_dict.get("AmountMinorUnits", "")),
            str(attempt_dict.get("Currency", "")),
            str(attempt_dict.get("Status", "")),
            str(attempt_dict.get("AttemptTokenHash", "")),
            str(attempt_dict.get("TokenCreatedAt", "")),
            str(attempt_dict.get("TokenExpiresAt", "")),
            str(attempt_dict.get("StartedAt", "")),
            str(attempt_dict.get("Deadline", "")),
            str(attempt_dict.get("CompletedAt", "")),
            str(attempt_dict.get("Score", "")),
            str(attempt_dict.get("StrikeCount", 0)),
            str(attempt_dict.get("SessionID", "")),
            str(attempt_dict.get("LastSeenAt", "")),
            str(attempt_dict.get("QuestionOrderJSON", "")),
            str(attempt_dict.get("OptionOrderJSON", "")),
            str(attempt_dict.get("SubmissionHash", "")),
            str(attempt_dict.get("Timestamp", ""))
        ]
        cell = ws.find(attempt_id)
        if cell:
            ws.update(values=[row], range_name=f"A{cell.row}:Y{cell.row}")
        else:
            ws.append_row(row)

    @retry_with_backoff(retries=3, initial_delay=0.1)
    def sync_webhook_event(self, event_dict: Dict[str, Any]):
        """Appends a webhook event into the WebhookEvents worksheet with retries."""
        if not self.is_configured or not self.spreadsheet:
            return
        ws = self.spreadsheet.worksheet("WebhookEvents")
        event_id = str(event_dict.get("EventID", ""))
        cell = ws.find(event_id)
        if cell:
            return
        row = [
            event_id,
            str(event_dict.get("EventType", "")),
            str(event_dict.get("OrderID", "")),
            str(event_dict.get("PaymentID", "")),
            str(event_dict.get("ReceivedAt", "")),
            str(event_dict.get("ProcessedAt", "")),
            str(event_dict.get("ProcessingStatus", "PROCESSED")),
            str(event_dict.get("ErrorMessage", ""))
        ]
        ws.append_row(row)

sheets_service = GoogleSheetsService()

