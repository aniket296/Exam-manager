# SmartAssess Junior - Online Assessment Website

A complete, responsive, child-friendly, and secure **browser-based online assessment website** designed specifically for school students up to approximately the 7th standard.

Built with a decoupled architecture:
* **Frontend Website:** Responsive Vanilla HTML5, CSS3, JavaScript (Razorpay Checkout SDK & jsPDF report generation).
* **Backend API:** Python FastAPI with strict authoritative security, Pydantic validation, and timezone-aware UTC datetime management.
* **Datastore:** High-integrity SQLite layer for ACID transactional locking and duplicate-submission prevention, paired with bidirectional Google Sheets synchronization (`gspread` with exponential backoff).

---

## 1. Architecture Overview

```text
                    PARENT / TEACHER / GUARDIAN
                                │
                                │ 1. Test Selection & Payment
                                ▼
                       ┌─────────────────┐
                       │    Razorpay     │
                       └────────┬────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────┐
│                   RESPONSIVE WEBSITE                   │
│                                                        │
│ HTML5 + CSS3 + Vanilla JavaScript                      │
│ Deployable on Netlify / Cloudflare Pages / Static CDN  │
│                                                        │
│ Works on Mobile, Tablets, Laptops & Desktop PCs (320px+)│
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS REST API
                            ▼
               ┌────────────────────────┐
               │    FastAPI Backend     │
               │    Trusted Authority   │
               └────────────┬───────────┘
                            │
               ┌────────────┴───────────┐
               ▼                        ▼
     ┌──────────────────┐     ┌──────────────────┐
     │  SQLite Storage  │     │  Google Sheets   │
     │  Atomic Locking  │     │  Provider Portal │
     │  Attempts/Orders │     │  Sync & Reports  │
     └──────────────────┘     └──────────────────┘
```

### Trust Boundary
* **Frontend (UNTRUSTED):** Runs in the student/parent browser. Never authoritative for test prices, payment statuses, scores, correct answers, anti-cheat strikes, or test deadlines.
* **Backend (TRUSTED):** Authoritatively controls all prices, Razorpay signature checks, exam session creation, question randomization snapshots, server deadlines, answer evaluations, and negative marking.

---

## 2. Directory Structure

```text
Exam manager/
├── backend/
│   ├── .env.example            # Environment variables template
│   ├── requirements.txt        # Production dependencies
│   ├── main.py                 # FastAPI application, CORS, security headers, seed data
│   ├── config.py               # Settings and configuration
│   ├── models.py               # SQLAlchemy schema (Papers, Orders, Attempts, Webhooks)
│   ├── schemas.py              # Pydantic input models & validation limits
│   ├── routers/
│   │   ├── admin.py            # Admin login, paper CRUD, publish/archive, results
│   │   ├── papers.py           # Public published test catalog
│   │   ├── payments.py         # Order creation, verification, raw-body webhooks
│   │   └── exams.py            # Exam start, heartbeat, anti-cheat events, submission
│   ├── services/
│   │   ├── sheets_service.py   # gspread Google Sheets sync with retry & backoff
│   │   ├── razorpay_service.py # Razorpay orders, HMAC-SHA256 signature verification
│   │   ├── exam_service.py     # Exam lifecycle, single-seed randomization, timer
│   │   ├── scoring_service.py  # Authoritative MCQ & normalized text grading
│   │   ├── token_service.py    # secrets.token_urlsafe & SHA-256 token hashing
│   │   └── webhook_service.py  # Idempotent webhook processor
│   ├── security/
│   │   ├── admin_auth.py       # PBKDF2 admin password verification & session tokens
│   │   ├── attempt_auth.py     # Bearer attempt token validation against database hash
│   │   └── rate_limit.py       # Thread-safe sliding window rate limiter
│   ├── utils/
│   │   ├── time.py             # UTC timezone-aware datetime helpers
│   │   ├── hashing.py          # SHA-256 and HMAC utilities
│   │   └── retry.py            # Exponential backoff retry decorator
│   └── tests/                  # Pytest test suite (100% passing)
│       ├── conftest.py
│       ├── test_papers.py
│       ├── test_payments.py
│       ├── test_exams.py
│       └── test_scoring.py
│
├── frontend/
│   ├── index.html              # Storefront catalog & parent enrollment modal
│   ├── exam.html               # Exam room: fullscreen start, server timer, questions
│   ├── result.html             # Scorecard, question review, jsPDF report download
│   ├── admin.html              # Teacher/Provider dashboard & question editor
│   ├── netlify.toml            # Netlify deployment rules & security headers
│   ├── _headers                # CSP, X-Content-Type-Options, Referrer-Policy
│   ├── css/
│   │   ├── style.css           # Mobile-first base styles & accessible palette
│   │   ├── exam.css            # Large touch targets, countdown timer, question palette
│   │   ├── result.css          # Printable score cards & certificate styling
│   │   └── admin.css           # Provider table & question builder layout
│   └── js/
│       ├── config.js           # API base URL & storage keys
│       ├── api.js              # Fetch wrapper with child-friendly error translations
│       ├── auth.js             # Session token manager (in-memory / sessionStorage)
│       ├── storefront.js       # Catalog loader & Razorpay payment orchestrator
│       ├── exam.js             # Timer sync, anti-cheat deterrence, submission handler
│       ├── result.js           # Scorecard viewer & jsPDF report generator
│       └── admin.js            # Admin authentication, paper builder & publisher
│
├── .gitignore
└── README.md
```

---

## 3. Quick Start (Local Development)

### Prerequisites
* Python 3.10+ (tested on Python 3.14)
* Modern web browser (Chrome, Edge, Firefox, Safari)

### Step 1: Backend Setup
1. Open a terminal in the project directory:
   ```bash
   cd "d:/projects/Exam manager"
   ```
2. Activate or initialize the virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp backend/.env.example backend/.env
   ```
   *(By default, `RAZORPAY_SIMULATION_MODE=true`, allowing instant end-to-end testing without external credentials).*
5. Run the automated test suite:
   ```bash
   python -m pytest backend/tests -v
   ```
6. Start the FastAPI backend server:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   API Docs will be available at: `http://localhost:8000/api/docs`.

### Step 2: Frontend Setup
1. Serve the `frontend/` directory with any static HTTP server (e.g. Python `http.server`, Live Server, or Nginx):
   ```bash
   python -m http.server 3000 --directory frontend
   ```
2. Open `http://localhost:3000` in your web browser.

---

## 4. Workflows

### A. Parent / Teacher Payment Workflow
1. Parent or teacher visits `http://localhost:3000`.
2. Reviews available tests (e.g. "Class 5-7 Math & Science Starter Challenge").
3. Clicks **Select Test**.
4. Enters student name (e.g. "Aarav Patel") and optional roll number or phone.
5. Clicks **Proceed to Pay & Start**.
6. The backend generates a Razorpay order with the **authoritative price**.
7. In simulation/live mode, the payment is verified against Razorpay signatures.
8. The backend generates an unguessable 32-byte `AttemptToken`, hashes it with SHA-256 in the database, and returns it securely to the client session.
9. The website automatically navigates to `exam.html` without exposing credentials in the URL.

### B. Student Exam Workflow (Child-Friendly & Calm)
1. **Pre-Exam Checklist:** Student sees friendly, calm instructions:
   * *Sit somewhere quiet.*
   * *Keep this test open.*
   * *Make sure your internet connection is working.*
   * *Your timer starts when you press Start Test.*
2. **Start Test:** Student taps **Start Test Now**.
   * Triggers browser fullscreen request.
   * Starts server-authoritative timer.
   * Freezes randomized question and MCQ option orders for the attempt.
3. **Taking the Test:**
   * Questions are presented with large touch targets (minimum 48px height).
   * Question palette on the side/bottom shows answered vs. unanswered questions.
   * Heartbeat sends background pulses every 30 seconds to keep the session alive.
4. **Anti-Cheat Deterrence:**
   * If the student switches tabs, blurs the window, or exits fullscreen, a polite, non-threatening modal appears:
     > *"Please stay on the test screen until you finish your questions."*
   * Violations are recorded authoritatively on the backend.
   * If the provider configured `AUTO_SUBMIT_ON_3`, reaching 3 strikes automatically finalizes and grades the test.
5. **Submission:**
   * Student taps **Submit Test ✓**.
   * Confirmation dialog confirms: *"You answered 5 out of 5 questions."*
   * Backend grades questions authoritatively, applying positive marks and negative marking penalties where configured.
   * Directs student to `result.html`.

### C. Result & PDF Report Card
1. Student and parent view the scorecard: Total Marks, Score, Percentage, Correct, Wrong, and Skipped counts.
2. If the paper's `ShowAnswerKey` setting is enabled, a detailed breakdown displays the student's answer alongside the correct answer.
3. Tapping **Download Report Card (PDF)** uses `jsPDF` to generate a report card ready for saving or printing.

### D. Provider / Admin Portal Workflow
1. Visit `http://localhost:3000/admin.html`.
2. Sign in with the admin password (Default: `Admin@12345`).
3. **Paper Management:**
   * Create new tests in `DRAFT` status.
   * Add MCQ questions with custom options and select the correct option.
   * Add text questions with comma-separated acceptable aliases (e.g. `delhi,new delhi`).
   * Set time limit, price in INR, negative marking flag, answer key visibility, and anti-cheat policy.
   * **Publish:** Performs strict validation (unique IDs, valid options, positive marks) and makes test live.
   * **Duplicate:** Clones published/archived papers to a new version draft for safe edits.
   * **Archive:** Safely hides tests without affecting historical attempts.
4. **Student Results Review:**
   * Real-time table of student scores, completion times, and anti-cheat strike counts.

---

## 5. Security Architecture (All 35 Rules Enforced)

| Security Rule | Backend Implementation |
| :--- | :--- |
| **Price Authority** | `POST /payments/create-order` strictly reads price from the backend `papers` table. Client prices are ignored. |
| **Razorpay Verification** | `POST /payments/verify` verifies HMAC-SHA256 signature (`order_id\|payment_id`) in constant time. |
| **Raw-Body Webhooks** | `POST /payments/webhook` verifies signatures directly over raw request bytes before JSON decoding. Idempotent by `EventID`. |
| **Exam Access Tokens** | 32-byte cryptographically secure tokens (`secrets.token_urlsafe(32)`). Only SHA-256 hashes are stored in the datastore. Never in URLs. |
| **Server-Side Deadlines** | Exam deadline is authoritatively set on exam start (`Deadline = StartedAt + TimeLimitMinutes`). Changing device clocks or localStorage cannot extend time. |
| **Persistent Randomization** | Question order and option orders are randomized ONCE on first start and frozen in `QuestionOrderJSON` and `OptionOrderJSON`. Reloading retains identical order. |
| **Hidden Answers** | `GET /exam` filters out `CorrectAnswer`, answer aliases, and correctness marks. Answers are never sent to the browser before submission. |
| **Authoritative Grading** | All grading occurs in `scoring_service.py`. Normalizes text responses (whitespace collapse, case insensitivity, aliases). |
| **Double-Click & Replay Protection** | Submissions transition `STARTED -> COMPLETED` under an atomic lock. Duplicate submissions return the cached score safely. |
| **XSS Protection** | Frontend utilizes `element.textContent` for all untrusted student, question, and result data. |
| **Security Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and restricted CSP. |

---

## 6. Google Sheets Integration

The platform automatically synchronizes with Google Sheets when configured via `gspread`:
* **`Papers` Worksheet:** Keeps provider-facing copies of paper metadata, versions, and question JSONs.
* **`Attempts` Worksheet:** Synchronizes student attempts, scores, and completion timestamps.
* **`WebhookEvents` Worksheet:** Logs Razorpay webhook events for audit and reconciliation.

### Google Service Account Setup
1. Create a Google Cloud Service Account with Google Sheets API and Google Drive API enabled.
2. Download the JSON key file.
3. Share your target Google Sheet with the service account email (as Editor).
4. Set the environment variables in `backend/.env`:
   ```env
   GOOGLE_SHEET_ID=your_google_sheet_id_here
   GOOGLE_SERVICE_ACCOUNT_PATH=path/to/service_account.json
   # Or paste inline JSON:
   # GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
   ```
*(If Google Sheets credentials are not set, the platform operates seamlessly using the local SQLite store).*

---

## 7. Deployment Instructions

### Frontend (Netlify)
1. Push this repository to GitHub or GitLab.
2. In Netlify, create a new site from your Git repository.
3. Set **Base directory** to `frontend`.
4. Set **Publish directory** to `.`.
5. In `frontend/js/config.js`, update `CONFIG.API_BASE_URL` to point to your deployed FastAPI backend (e.g. `https://api.yourdomain.com`).
6. Netlify will automatically apply the security headers and URL redirects configured in `frontend/netlify.toml` and `frontend/_headers`.

### Backend (Render, Railway, or VPS)
1. Deploy the `backend/` directory using Python 3.10+.
2. Set build command: `pip install -r backend/requirements.txt`
3. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
4. Configure production environment variables in your hosting dashboard:
   * `FRONTEND_URL=https://your-netlify-site.netlify.app`
   * `ENVIRONMENT=production`
   * `RAZORPAY_KEY_ID=rzp_live_...`
   * `RAZORPAY_KEY_SECRET=...`
   * `RAZORPAY_WEBHOOK_SECRET=...`
   * `RAZORPAY_SIMULATION_MODE=false`
   * `ADMIN_PASSWORD_HASH=...` (generate using `python -c "from backend.utils.hashing import hash_password; print(hash_password('YourStrongPassword'))"`)
   * `ADMIN_SECRET_KEY=...` (at least 32 random characters)
   * `GOOGLE_SHEET_ID=...`
   * `GOOGLE_SERVICE_ACCOUNT_JSON=...`

---

## 8. License

Educational Assessment Platform - Released for student and institutional learning.

