// Global Configuration for Online Assessment Website
const CONFIG = {
  // Base URL for the FastAPI Backend (works on localhost, Render, or any host)
  API_BASE_URL: window.location.origin,
  
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

