import gspread
from unittest.mock import MagicMock

class MockGSpreadAPIError(Exception):
    """Simulates gspread APIError with HTTP 429 Too Many Requests / Quota Exceeded."""
    def __init__(self, message="Quota exceeded for quota metric 'Read requests' and limit 'Read requests per minute'", code=429):
        super().__init__(message)
        self.code = code
        self.response = MagicMock()
        self.response.status_code = code

class MockWorksheet:
    def __init__(self, title="Papers", fail_count=0):
        self.title = title
        self.fail_count = fail_count
        self.call_count = 0
        self.rows = []

    def append_row(self, row, **kwargs):
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise MockGSpreadAPIError("429 RESOURCE_EXHAUSTED: Quota exceeded", code=429)
        self.rows.append(row)
        return {"updates": {"updatedRows": 1}}

    def find(self, query):
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise MockGSpreadAPIError("429 RESOURCE_EXHAUSTED: Quota exceeded", code=429)
        return None

    def update(self, values=None, range_name=None, **kwargs):
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise MockGSpreadAPIError("429 RESOURCE_EXHAUSTED: Quota exceeded", code=429)
        return {"updatedRange": range_name}


    def row_values(self, row_index):
        return ["Header1", "Header2"]

class MockSpreadsheet:
    def __init__(self, fail_count=0):
        self.fail_count = fail_count
        self.worksheets_map = {
            "Papers": MockWorksheet("Papers", fail_count),
            "Attempts": MockWorksheet("Attempts", fail_count),
            "WebhookEvents": MockWorksheet("WebhookEvents", fail_count)
        }

    def worksheet(self, name):
        return self.worksheets_map.get(name, MockWorksheet(name, self.fail_count))

    def worksheets(self):
        return list(self.worksheets_map.values())

    def add_worksheet(self, title, rows, cols):
        ws = MockWorksheet(title, self.fail_count)
        self.worksheets_map[title] = ws
        return ws

