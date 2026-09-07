// Exam Room Client Controller
document.addEventListener("DOMContentLoaded", () => {
  const token = Auth.getAttemptToken();
  const preExamCard = document.getElementById("preExamCard");
  const preExamError = document.getElementById("preExamError");
  const startExamBtn = document.getElementById("startExamBtn");
  const examHeader = document.getElementById("examHeader");
  const activeExamRoom = document.getElementById("activeExamRoom");
  const examTitleHeader = document.getElementById("examTitleHeader");
  const examStudentNameHeader = document.getElementById("examStudentNameHeader");
  const timerDisplay = document.getElementById("timerDisplay");
  const examTimerBox = document.getElementById("examTimerBox");
  const progressFill = document.getElementById("progressFill");

  const questionCounter = document.getElementById("questionCounter");
  const questionMarks = document.getElementById("questionMarks");
  const questionText = document.getElementById("questionText");
  const questionImageWrap = document.getElementById("questionImageWrap");
  const questionImage = document.getElementById("questionImage");
  const optionsContainer = document.getElementById("optionsContainer");
  const textAnswerContainer = document.getElementById("textAnswerContainer");
  const textAnswerInput = document.getElementById("textAnswerInput");
  const prevQuestionBtn = document.getElementById("prevQuestionBtn");
  const nextQuestionBtn = document.getElementById("nextQuestionBtn");
  const submitExamBtn = document.getElementById("submitExamBtn");
  const paletteGrid = document.getElementById("paletteGrid");

  const confirmSubmitDialog = document.getElementById("confirmSubmitDialog");
  const submitSummaryText = document.getElementById("submitSummaryText");
  const cancelSubmitBtn = document.getElementById("cancelSubmitBtn");
  const finalSubmitBtn = document.getElementById("finalSubmitBtn");

  const antiCheatDialog = document.getElementById("antiCheatDialog");
  const antiCheatMessage = document.getElementById("antiCheatMessage");
  const closeWarningBtn = document.getElementById("closeWarningBtn");

  // State
  let examData = null;
  let currentIndex = 0;
  let answers = {};
  let timerInterval = null;
  let heartbeatInterval = null;
  let isSubmitting = false;
  let hasStarted = false;

  // 1. Initial Access Check
  if (!token) {
    preExamCard.innerHTML = `
      <div style="font-size: 3rem; margin-bottom: 0.5rem;">🔒</div>
      <h2>No Active Test Found</h2>
      <p style="color: var(--text-muted); margin: 1rem 0 1.5rem 0;">
        Please select a test and complete enrollment first.
      </p>
      <a href="index.html" class="btn btn-primary btn-lg">Browse Available Tests</a>
    `;
    return;
  }

  // Load saved local answers for reload recovery (usability only - Section 31)
  try {
    const saved = sessionStorage.getItem(CONFIG.STORAGE_KEYS.SAVED_ANSWERS);
    if (saved) answers = JSON.parse(saved);
  } catch (e) {
    answers = {};
  }

  // 2. Start Exam Handler
  startExamBtn.addEventListener("click", async () => {
    startExamBtn.disabled = true;
    startExamBtn.textContent = "Preparing your test...";
    preExamError.style.display = "none";

    // Request Fullscreen on explicit user interaction (Section 34 & 38)
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      } else if (document.documentElement.webkitRequestFullscreen) {
        await document.documentElement.webkitRequestFullscreen();
      }
    } catch (fsErr) {
      console.warn("Fullscreen permission skipped or unavailable:", fsErr);
    }

    try {
      // Authenticated Exam Start / Resume
      examData = await API.get("/exam", Auth.getExamHeaders());
      hasStarted = true;

      // Populate Headers
      examTitleHeader.textContent = examData.PaperTitle;
      examStudentNameHeader.textContent = `Student: ${examData.StudentName}`;

      // Switch UI
      preExamCard.style.display = "none";
      examHeader.style.display = "block";
      activeExamRoom.style.display = "grid";

      // Initialize Authoritative Timer
      initTimer(examData.Deadline);

      // Start Periodic Heartbeat (every 30s)
      initHeartbeat();

      // Render Question Navigator & First Question
      renderPalette();
      showQuestion(0);

      // Attach Anti-Cheat Deterrence Listeners
      setupAntiCheat();

    } catch (err) {
      startExamBtn.disabled = false;
      startExamBtn.textContent = "🚀 Start Test Now";
      preExamError.textContent = err.message || "Failed to start test. Please try again.";
      preExamError.style.display = "block";
    }
  });

  // 3. Authoritative Timer Countdown (Section 30)
  function initTimer(deadlineIso) {
    if (timerInterval) clearInterval(timerInterval);

    function update() {
      const now = new Date().getTime();
      const end = new Date(deadlineIso).getTime();
      const remainingSeconds = Math.max(0, Math.floor((end - now) / 1000));

      const mins = Math.floor(remainingSeconds / 60);
      const secs = remainingSeconds % 60;
      timerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      // Visual warning when less than 2 minutes remain
      if (remainingSeconds <= 120) {
        examTimerBox.classList.add("timer-warning");
      } else {
        examTimerBox.classList.remove("timer-warning");
      }

      if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        handleTimeExpired();
      }
    }

    update();
    timerInterval = setInterval(update, 1000);
  }

  function handleTimeExpired() {
    if (isSubmitting) return;
    isSubmitting = true;
    timerDisplay.textContent = "00:00";
    alert("Time is up! Your answers are being submitted now.");
    executeSubmission();
  }

  // 4. Heartbeat Sync (Section 33)
  function initHeartbeat() {
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    heartbeatInterval = setInterval(async () => {
      if (!hasStarted || isSubmitting) return;
      try {
        const hb = await API.post("/exam/heartbeat", {
          SessionID: examData.SessionID,
          CurrentQuestionID: examData.Questions[currentIndex]?.QuestionID
        }, Auth.getExamHeaders());

        if (hb && hb.Deadline) {
          // Keep timer authoritative
          initTimer(hb.Deadline);
        }
      } catch (err) {
        console.warn("Heartbeat missed (network jitter):", err.message);
      }
    }, 30000);
  }

  // 5. Anti-Cheat Deterrence Handlers (Section 34, 35, 36, 37)
  let blurTimer = null;
  let isReloading = false;

  window.addEventListener("beforeunload", () => {
    isReloading = true;
    if (blurTimer) {
      clearTimeout(blurTimer);
      blurTimer = null;
    }
  });

  function setupAntiCheat() {
    // Visibility change (tab switch - flag after tab is hidden)
    document.addEventListener("visibilitychange", () => {
      if (!hasStarted || isSubmitting || isReloading) return;
      if (document.hidden) {
        reportEvent("TAB_HIDDEN", "User switched away from test tab.");
      }
    });

    // Window blur with 2-second grace period (mobile notification / brief blur simulation)
    window.addEventListener("blur", () => {
      if (!hasStarted || isSubmitting || isReloading) return;
      if (blurTimer) clearTimeout(blurTimer);
      blurTimer = setTimeout(() => {
        if (!document.hasFocus() && !isReloading && !isSubmitting) {
          reportEvent("WINDOW_BLUR", "Browser window lost focus for more than 2 seconds.");
        }
      }, 2000);
    });

    window.addEventListener("focus", () => {
      if (blurTimer) {
        clearTimeout(blurTimer);
        blurTimer = null;
      }
    });

    // Fullscreen exit
    document.addEventListener("fullscreenchange", () => {
      if (!hasStarted || isSubmitting || isReloading) return;
      if (!document.fullscreenElement) {
        reportEvent("FULLSCREEN_EXIT", "User exited fullscreen mode.");
      }
    });

    // Action locks: Copy, Cut, Paste, Context Menu
    document.addEventListener("copy", (e) => {
      if (!hasStarted) return;
      e.preventDefault();
      reportEvent("COPY_ATTEMPT", "Copy prohibited during assessment.");
    });

    document.addEventListener("cut", (e) => {
      if (!hasStarted) return;
      e.preventDefault();
      reportEvent("CUT_ATTEMPT", "Cut prohibited during assessment.");
    });

    document.addEventListener("paste", (e) => {
      if (!hasStarted) return;
      e.preventDefault();
      reportEvent("PASTE_ATTEMPT", "Paste prohibited during assessment.");
    });

    document.addEventListener("contextmenu", (e) => {
      if (hasStarted) e.preventDefault();
    });

    // Keydown locks: F12, PrintScreen, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+P
    document.addEventListener("keydown", (e) => {
      if (!hasStarted) return;
      if (e.key === "F12" || e.key === "PrintScreen" || e.keyCode === 44) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      if (e.ctrlKey || e.metaKey) {
        const k = e.key.toLowerCase();
        if (k === "c" || k === "v" || k === "x" || k === "p") {
          e.preventDefault();
          e.stopPropagation();
          return;
        }
      }
    });
  }

  let eventDebounce = false;
  async function reportEvent(eventType, details) {
    if (eventDebounce || isSubmitting) return;
    eventDebounce = true;
    setTimeout(() => { eventDebounce = false; }, 2000);

    try {
      const res = await API.post("/exam/event", {
        EventType: eventType,
        Details: details
      }, Auth.getExamHeaders());

      if (res.ActionTaken === "AUTO_SUBMITTED") {
        antiCheatMessage.textContent = res.FriendlyMessage;
        if (typeof antiCheatDialog.showModal === "function") antiCheatDialog.showModal();
        setTimeout(() => {
          executeSubmission();
        }, 2000);
      } else {
        antiCheatMessage.textContent = res.FriendlyMessage;
        if (typeof antiCheatDialog.showModal === "function") {
          antiCheatDialog.showModal();
        }
      }
    } catch (err) {
      console.warn("Anti-cheat event reporting skipped:", err);
    }
  }

  closeWarningBtn.addEventListener("click", () => {
    if (typeof antiCheatDialog.close === "function") antiCheatDialog.close();
  });

  // 6. Question Rendering & Interaction
  function showQuestion(index) {
    if (!examData || !examData.Questions || examData.Questions.length === 0) return;
    currentIndex = index;
    const q = examData.Questions[currentIndex];
    const total = examData.Questions.length;

    // Update Progress
    questionCounter.textContent = `Question ${currentIndex + 1} of ${total}`;
    const pct = ((currentIndex + 1) / total) * 100;
    progressFill.style.width = `${pct}%`;

    // Marks info
    const negText = examData.NegativeMarkingEnabled && q.MarksNegative > 0
      ? ` | -${q.MarksNegative} if wrong`
      : ``;
    questionMarks.textContent = `+${q.MarksCorrect} Marks${negText}`;

    // Question Text (Safe textContent)
    questionText.textContent = q.QuestionText;

    // Image
    if (q.ImageURL && q.ImageURL.trim() !== "") {
      questionImage.src = q.ImageURL;
      questionImage.alt = q.ImageAltText || "Question illustration";
      questionImageWrap.style.display = "block";
    } else {
      questionImageWrap.style.display = "none";
    }

    // MCQ vs Text layout
    optionsContainer.innerHTML = "";
    if (q.Type === "MCQ") {
      textAnswerContainer.style.display = "none";
      optionsContainer.style.display = "flex";

      q.Options.forEach(opt => {
        const item = document.createElement("div");
        item.className = "option-item";
        if (answers[q.QuestionID] === opt.OptionID) {
          item.classList.add("selected");
        }

        const indicator = document.createElement("div");
        indicator.className = "option-indicator";

        const label = document.createElement("span");
        label.className = "option-text";
        label.textContent = opt.Text; // Safe text rendering

        item.appendChild(indicator);
        item.appendChild(label);

        item.addEventListener("click", () => {
          answers[q.QuestionID] = opt.OptionID;
          saveLocalAnswers();
          showQuestion(currentIndex); // refresh current selection
          updatePaletteButtons();
        });

        optionsContainer.appendChild(item);
      });
    } else if (q.Type === "Text") {
      optionsContainer.style.display = "none";
      textAnswerContainer.style.display = "block";
      textAnswerInput.value = answers[q.QuestionID] || "";
    }

    // Prev / Next button states
    prevQuestionBtn.style.visibility = currentIndex === 0 ? "hidden" : "visible";
    if (currentIndex === total - 1) {
      nextQuestionBtn.style.display = "none";
    } else {
      nextQuestionBtn.style.display = "inline-flex";
    }

    updatePaletteButtons();
  }

  // Text input listener
  textAnswerInput.addEventListener("input", () => {
    if (!examData) return;
    const q = examData.Questions[currentIndex];
    answers[q.QuestionID] = textAnswerInput.value;
    saveLocalAnswers();
    updatePaletteButtons();
  });

  function saveLocalAnswers() {
    try {
      const serialized = JSON.stringify(answers);
      sessionStorage.setItem(CONFIG.STORAGE_KEYS.SAVED_ANSWERS, serialized);
      localStorage.setItem(CONFIG.STORAGE_KEYS.SAVED_ANSWERS, serialized);
    } catch (e) {}
  }

  // 7. Navigation Buttons
  prevQuestionBtn.addEventListener("click", () => {
    if (currentIndex > 0) showQuestion(currentIndex - 1);
  });

  nextQuestionBtn.addEventListener("click", () => {
    if (currentIndex < examData.Questions.length - 1) showQuestion(currentIndex + 1);
  });

  // 8. Palette Rendering
  function renderPalette() {
    paletteGrid.innerHTML = "";
    examData.Questions.forEach((q, idx) => {
      const btn = document.createElement("button");
      btn.className = "palette-btn";
      btn.textContent = idx + 1;
      btn.setAttribute("aria-label", `Jump to question ${idx + 1}`);
      btn.addEventListener("click", () => showQuestion(idx));
      paletteGrid.appendChild(btn);
    });
  }

  function updatePaletteButtons() {
    const buttons = paletteGrid.querySelectorAll(".palette-btn");
    examData.Questions.forEach((q, idx) => {
      const btn = buttons[idx];
      if (!btn) return;

      const isAnswered = answers[q.QuestionID] && answers[q.QuestionID].trim() !== "";
      if (isAnswered) {
        btn.classList.add("answered");
      } else {
        btn.classList.remove("answered");
      }

      if (idx === currentIndex) {
        btn.classList.add("current");
      } else {
        btn.classList.remove("current");
      }
    });
  }

  // 9. Submission Flow (Section 41, 42)
  submitExamBtn.addEventListener("click", () => {
    const total = examData.Questions.length;
    let answeredCount = 0;
    examData.Questions.forEach(q => {
      if (answers[q.QuestionID] && answers[q.QuestionID].trim() !== "") {
        answeredCount++;
      }
    });

    submitSummaryText.textContent = `You answered ${answeredCount} out of ${total} questions.`;
    if (typeof confirmSubmitDialog.showModal === "function") {
      confirmSubmitDialog.showModal();
    } else {
      confirmSubmitDialog.setAttribute("open", "true");
    }
  });

  cancelSubmitBtn.addEventListener("click", () => {
    if (typeof confirmSubmitDialog.close === "function") {
      confirmSubmitDialog.close();
    } else {
      confirmSubmitDialog.removeAttribute("open");
    }
  });

  finalSubmitBtn.addEventListener("click", () => {
    if (typeof confirmSubmitDialog.close === "function") confirmSubmitDialog.close();
    executeSubmission();
  });

  async function executeSubmission() {
    if (isSubmitting) return;
    isSubmitting = true;

    if (timerInterval) clearInterval(timerInterval);
    if (heartbeatInterval) clearInterval(heartbeatInterval);

    // Disable all interaction
    submitExamBtn.disabled = true;
    submitExamBtn.textContent = "Grading Test...";

    try {
      const result = await API.post("/exam/submit", {
        Answers: answers
      }, Auth.getExamHeaders());

      // Save result for scorecard page
      sessionStorage.setItem("last_exam_result", JSON.stringify(result));
      // Clean attempt token since attempt is completed
      Auth.clearAttemptSession();

      // Redirect to Result Page
      window.location.href = "result.html";
    } catch (err) {
      alert(err.message || "Failed to submit test. Please contact your teacher.");
      isSubmitting = false;
      submitExamBtn.disabled = false;
      submitExamBtn.textContent = "Submit Test ✓";
    }
  }
});

