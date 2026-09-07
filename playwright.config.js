// Playwright configuration with automated dual webServer startup
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  testMatch: /.*\.spec\.js/,
  timeout: 30000,
  expect: {
    timeout: 6000
  },
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
    headless: true
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    }
  ],
  webServer: [
    {
      command: '.venv\\Scripts\\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 15000
    },
    {
      command: '.venv\\Scripts\\python -m http.server 3000 --directory frontend',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: true,
      timeout: 15000
    }
  ]
});

