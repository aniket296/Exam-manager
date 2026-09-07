// Global Configuration for Online Assessment Website
const CONFIG = {
  // Base URL for the FastAPI Backend.
  // In development, default to http://localhost:8000.
  // In production, can be configured or set to backend domain.
  API_BASE_URL: window.EXAM_API_BASE_URL || (
    window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? "http://localhost:8000"
      : "https://your-api-domain.com"
  ),
  
  // Storage keys for browser recovery (usability only, backend is authority)
  STORAGE_KEYS: {
    ATTEMPT_TOKEN: "exam_attempt_token",
    ATTEMPT_ID: "exam_attempt_id",
    PAPER_ID: "exam_paper_id",
    STUDENT_NAME: "exam_student_name",
    SAVED_ANSWERS: "exam_saved_answers",
    ADMIN_TOKEN: "exam_admin_token"
  }
};

