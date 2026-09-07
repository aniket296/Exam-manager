// Centralized API client with friendly error handling
const API = {
  async request(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(url, config);
      let data = null;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        // Translate technical errors into child/parent friendly messages
        let friendlyMessage = "Something went wrong. Please check your internet connection.";
        
        if (response.status === 401) {
          friendlyMessage = "Your test session has ended or could not be verified. Please contact your teacher.";
        } else if (response.status === 404) {
          friendlyMessage = "This assessment was not found or is no longer available.";
        } else if (response.status === 409) {
          friendlyMessage = (data && data.detail) || "This test has already been completed.";
        } else if (response.status === 410) {
          friendlyMessage = "The time limit for this test has ended.";
        } else if (response.status === 429) {
          friendlyMessage = "Please wait a moment before trying again.";
        } else if (response.status === 422) {
          friendlyMessage = (data && data.detail) || "Please check your answers or details and try again.";
        } else if (response.status >= 500) {
          friendlyMessage = "The test server is taking a quick break. Please wait a few seconds and try again.";
        } else if (data && data.detail && typeof data.detail === "string") {
          friendlyMessage = data.detail;
        }

        const error = new Error(friendlyMessage);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        // Network connection error
        const netErr = new Error("Could not connect to the test server. Please check your internet.");
        netErr.status = 0;
        throw netErr;
      }
      throw err;
    }
  },

  get(endpoint, headers = {}) {
    return this.request(endpoint, { method: "GET", headers });
  },

  post(endpoint, body, headers = {}) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
      headers
    });
  },

  put(endpoint, body, headers = {}) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
      headers
    });
  }
};

