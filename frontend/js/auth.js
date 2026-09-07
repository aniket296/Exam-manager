// Authentication & Session Management
const Auth = {
  // --- Student Attempt Auth ---
  getAttemptToken() {
    return sessionStorage.getItem(CONFIG.STORAGE_KEYS.ATTEMPT_TOKEN);
  },

  getAttemptId() {
    return sessionStorage.getItem(CONFIG.STORAGE_KEYS.ATTEMPT_ID);
  },

  getStudentName() {
    return sessionStorage.getItem(CONFIG.STORAGE_KEYS.STUDENT_NAME);
  },

  setAttemptSession(token, attemptId, studentName, paperId) {
    if (token) sessionStorage.setItem(CONFIG.STORAGE_KEYS.ATTEMPT_TOKEN, token);
    if (attemptId) sessionStorage.setItem(CONFIG.STORAGE_KEYS.ATTEMPT_ID, attemptId);
    if (studentName) sessionStorage.setItem(CONFIG.STORAGE_KEYS.STUDENT_NAME, studentName);
    if (paperId) sessionStorage.setItem(CONFIG.STORAGE_KEYS.PAPER_ID, paperId);
  },

  clearAttemptSession() {
    sessionStorage.removeItem(CONFIG.STORAGE_KEYS.ATTEMPT_TOKEN);
    sessionStorage.removeItem(CONFIG.STORAGE_KEYS.ATTEMPT_ID);
    sessionStorage.removeItem(CONFIG.STORAGE_KEYS.STUDENT_NAME);
    sessionStorage.removeItem(CONFIG.STORAGE_KEYS.PAPER_ID);
    sessionStorage.removeItem(CONFIG.STORAGE_KEYS.SAVED_ANSWERS);
  },

  getExamHeaders() {
    const token = this.getAttemptToken();
    if (!token) return {};
    return {
      "Authorization": `Bearer ${token}`
    };
  },

  // --- Admin Auth ---
  getAdminToken() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.ADMIN_TOKEN);
  },

  setAdminToken(token) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.ADMIN_TOKEN, token);
  },

  clearAdminToken() {
    localStorage.removeItem(CONFIG.STORAGE_KEYS.ADMIN_TOKEN);
  },

  getAdminHeaders() {
    const token = this.getAdminToken();
    if (!token) return {};
    return {
      "Authorization": `Bearer ${token}`
    };
  }
};

