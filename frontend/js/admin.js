// Admin Portal Controller
document.addEventListener("DOMContentLoaded", () => {
  const loginCard = document.getElementById("loginCard");
  const loginForm = document.getElementById("loginForm");
  const loginError = document.getElementById("loginError");
  const adminPassword = document.getElementById("adminPassword");
  const adminHeaderNav = document.getElementById("adminHeaderNav");
  const logoutBtn = document.getElementById("logoutBtn");

  const dashboardView = document.getElementById("dashboardView");
  const tabPapersBtn = document.getElementById("tabPapersBtn");
  const tabResultsBtn = document.getElementById("tabResultsBtn");
  const tabPapersContent = document.getElementById("tabPapersContent");
  const tabResultsContent = document.getElementById("tabResultsContent");

  const papersTableBody = document.getElementById("papersTableBody");
  const attemptsTableBody = document.getElementById("attemptsTableBody");
  const openNewPaperModalBtn = document.getElementById("openNewPaperModalBtn");

  const paperEditorModal = document.getElementById("paperEditorModal");
  const paperEditorForm = document.getElementById("paperEditorForm");
  const editorModalTitle = document.getElementById("editorModalTitle");
  const closeEditorBtn = document.getElementById("closeEditorBtn");
  const cancelEditorBtn = document.getElementById("cancelEditorBtn");
  const editorError = document.getElementById("editorError");

  const paperTitleInput = document.getElementById("paperTitleInput");
  const paperPriceInput = document.getElementById("paperPriceInput");
  const paperTimeInput = document.getElementById("paperTimeInput");
  const antiCheatSelect = document.getElementById("antiCheatSelect");
  const negMarkingCheckbox = document.getElementById("negMarkingCheckbox");
  const showAnswerKeyCheckbox = document.getElementById("showAnswerKeyCheckbox");

  const addMcqBtn = document.getElementById("addMcqBtn");
  const addTextBtn = document.getElementById("addTextBtn");
  const questionsBuilderList = document.getElementById("questionsBuilderList");
  const questionCountLabel = document.getElementById("questionCountLabel");

  let editingPaperId = null;
  let builderQuestions = [];

  // Check initial login state
  if (Auth.getAdminToken()) {
    showDashboard();
  } else {
    showLogin();
  }

  function showLogin() {
    loginCard.style.display = "block";
    dashboardView.style.display = "none";
    adminHeaderNav.style.display = "none";
  }

  function showDashboard() {
    loginCard.style.display = "none";
    dashboardView.style.display = "block";
    adminHeaderNav.style.display = "flex";
    loadPapers();
  }

  // Handle Login
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.style.display = "none";
    const password = adminPassword.value;

    try {
      const res = await API.post("/admin/login", { Password: password });
      Auth.setAdminToken(res.Token);
      adminPassword.value = "";
      showDashboard();
    } catch (err) {
      loginError.textContent = err.message || "Invalid admin password.";
      loginError.style.display = "block";
    }
  });

  logoutBtn.addEventListener("click", () => {
    Auth.clearAdminToken();
    showLogin();
  });

  // Tab Switching
  tabPapersBtn.addEventListener("click", () => {
    tabPapersBtn.classList.add("active");
    tabResultsBtn.classList.remove("active");
    tabPapersContent.style.display = "block";
    tabResultsContent.style.display = "none";
    loadPapers();
  });

  tabResultsBtn.addEventListener("click", () => {
    tabResultsBtn.classList.add("active");
    tabPapersBtn.classList.remove("active");
    tabResultsContent.style.display = "block";
    tabPapersContent.style.display = "none";
    loadAttempts();
  });

  // Load Papers
  async function loadPapers() {
    try {
      const papers = await API.get("/admin/papers", Auth.getAdminHeaders());
      papersTableBody.innerHTML = "";

      if (!papers || papers.length === 0) {
        papersTableBody.innerHTML = `
          <tr><td colspan="6" style="text-align: center; padding: 2rem;">No papers created yet.</td></tr>
        `;
        return;
      }

      papers.forEach(p => {
        const tr = document.createElement("tr");

        const tdTitle = document.createElement("td");
        tdTitle.innerHTML = `<strong>${escapeHtml(p.Title)}</strong><br><small style="color: var(--text-muted);">${p.Questions.length} Questions</small>`;

        const tdPrice = document.createElement("td");
        tdPrice.textContent = p.PriceMinorUnits === 0 ? "Free" : `₹${(p.PriceMinorUnits / 100).toFixed(0)}`;

        const tdTime = document.createElement("td");
        tdTime.textContent = `${p.TimeLimitMinutes}m`;

        const tdVer = document.createElement("td");
        tdVer.textContent = `v${p.Version}`;

        const tdStatus = document.createElement("td");
        const statusBadge = document.createElement("span");
        statusBadge.className = `status-badge ${p.Status.toLowerCase()}`;
        statusBadge.textContent = p.Status;
        tdStatus.appendChild(statusBadge);

        const tdActions = document.createElement("td");
        tdActions.className = "table-actions";

        if (p.Status === "DRAFT") {
          const editBtn = document.createElement("button");
          editBtn.className = "btn btn-secondary";
          editBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          editBtn.textContent = "Edit";
          editBtn.addEventListener("click", () => openEditorForEdit(p));
          tdActions.appendChild(editBtn);

          const pubBtn = document.createElement("button");
          pubBtn.className = "btn btn-success";
          pubBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          pubBtn.textContent = "Publish";
          pubBtn.addEventListener("click", () => handlePublish(p.PaperID));
          tdActions.appendChild(pubBtn);
        } else if (p.Status === "PUBLISHED") {
          const dupBtn = document.createElement("button");
          dupBtn.className = "btn btn-secondary";
          dupBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          dupBtn.textContent = "Duplicate";
          dupBtn.addEventListener("click", () => handleDuplicate(p.PaperID));
          tdActions.appendChild(dupBtn);

          const arcBtn = document.createElement("button");
          arcBtn.className = "btn btn-danger";
          arcBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          arcBtn.textContent = "Archive";
          arcBtn.addEventListener("click", () => handleArchive(p.PaperID));
          tdActions.appendChild(arcBtn);
        } else if (p.Status === "ARCHIVED") {
          const dupBtn = document.createElement("button");
          dupBtn.className = "btn btn-secondary";
          dupBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          dupBtn.textContent = "Duplicate to Draft";
          dupBtn.addEventListener("click", () => handleDuplicate(p.PaperID));
          tdActions.appendChild(dupBtn);
        }

        tr.appendChild(tdTitle);
        tr.appendChild(tdPrice);
        tr.appendChild(tdTime);
        tr.appendChild(tdVer);
        tr.appendChild(tdStatus);
        tr.appendChild(tdActions);
        papersTableBody.appendChild(tr);
      });
    } catch (err) {
      if (err.status === 401) {
        Auth.clearAdminToken();
        showLogin();
      } else {
        alert(err.message || "Failed to load papers.");
      }
    }
  }

  // Load Attempts
  async function loadAttempts() {
    try {
      const attempts = await API.get("/admin/attempts", Auth.getAdminHeaders());
      attemptsTableBody.innerHTML = "";

      if (!attempts || attempts.length === 0) {
        attemptsTableBody.innerHTML = `
          <tr><td colspan="7" style="text-align: center; padding: 2rem;">No attempts recorded yet.</td></tr>
        `;
        return;
      }

      attempts.forEach(a => {
        const tr = document.createElement("tr");

        const tdStudent = document.createElement("td");
        tdStudent.innerHTML = `<strong>${escapeHtml(a.Name)}</strong>`;

        const tdRoll = document.createElement("td");
        tdRoll.textContent = a.StudentIdentifier || "-";

        const tdPaper = document.createElement("td");
        tdPaper.textContent = a.PaperID;

        const tdScore = document.createElement("td");
        tdScore.textContent = a.Score !== null ? `${a.Score} / ${a.MaxMarks || '-'}` : "In Progress";

        const tdStrikes = document.createElement("td");
        tdStrikes.textContent = a.StrikeCount;

        const tdStatus = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `status-badge ${a.Status.toLowerCase()}`;
        badge.textContent = a.Status;
        tdStatus.appendChild(badge);

        const tdCompleted = document.createElement("td");
        tdCompleted.textContent = a.CompletedAt ? new Date(a.CompletedAt).toLocaleString() : "-";

        tr.appendChild(tdStudent);
        tr.appendChild(tdRoll);
        tr.appendChild(tdPaper);
        tr.appendChild(tdScore);
        tr.appendChild(tdStrikes);
        tr.appendChild(tdStatus);
        tr.appendChild(tdCompleted);
        attemptsTableBody.appendChild(tr);
      });
    } catch (err) {
      alert(err.message || "Failed to load attempts.");
    }
  }

  // Actions
  async function handlePublish(paperId) {
    if (!confirm("Are you sure you want to publish this assessment paper? It will immediately become live for students.")) return;
    try {
      await API.post(`/admin/paper/${paperId}/publish`, {}, Auth.getAdminHeaders());
      loadPapers();
    } catch (err) {
      alert(err.message || "Publish failed.");
    }
  }

  async function handleArchive(paperId) {
    if (!confirm("Archive this paper? It will no longer be visible on the public website.")) return;
    try {
      await API.post(`/admin/paper/${paperId}/archive`, {}, Auth.getAdminHeaders());
      loadPapers();
    } catch (err) {
      alert(err.message || "Archive failed.");
    }
  }

  async function handleDuplicate(paperId) {
    try {
      await API.post(`/admin/paper/${paperId}/duplicate`, {}, Auth.getAdminHeaders());
      loadPapers();
    } catch (err) {
      alert(err.message || "Duplicate failed.");
    }
  }

  // Paper Editor Modal
  openNewPaperModalBtn.addEventListener("click", () => {
    editingPaperId = null;
    editorModalTitle.textContent = "Create New Assessment Paper";
    paperEditorForm.reset();
    paperPriceInput.value = "49";
    paperTimeInput.value = "20";
    builderQuestions = [];
    renderBuilderQuestions();
    editorError.style.display = "none";
    if (typeof paperEditorModal.showModal === "function") paperEditorModal.showModal();
  });

  function openEditorForEdit(paper) {
    editingPaperId = paper.PaperID;
    editorModalTitle.textContent = `Edit Draft Paper (${paper.PaperID})`;
    paperTitleInput.value = paper.Title;
    paperPriceInput.value = Math.floor(paper.PriceMinorUnits / 100);
    paperTimeInput.value = paper.TimeLimitMinutes;
    antiCheatSelect.value = paper.AntiCheatPolicy;
    negMarkingCheckbox.checked = paper.NegativeMarkingEnabled;
    showAnswerKeyCheckbox.checked = paper.ShowAnswerKey;

    builderQuestions = JSON.parse(JSON.stringify(paper.Questions || []));
    renderBuilderQuestions();
    editorError.style.display = "none";
    if (typeof paperEditorModal.showModal === "function") paperEditorModal.showModal();
  }

  closeEditorBtn.addEventListener("click", () => {
    if (typeof paperEditorModal.close === "function") paperEditorModal.close();
  });
  cancelEditorBtn.addEventListener("click", () => {
    if (typeof paperEditorModal.close === "function") paperEditorModal.close();
  });

  // Builder Questions Management
  addMcqBtn.addEventListener("click", () => {
    const qid = `Q${builderQuestions.length + 1}`;
    builderQuestions.push({
      QuestionID: qid,
      QuestionText: "",
      ImageURL: "",
      Type: "MCQ",
      Options: [
        { OptionID: "OPT1", Text: "" },
        { OptionID: "OPT2", Text: "" },
        { OptionID: "OPT3", Text: "" },
        { OptionID: "OPT4", Text: "" }
      ],
      CorrectAnswer: "OPT1",
      MarksCorrect: 4.0,
      MarksNegative: 1.0
    });
    renderBuilderQuestions();
  });

  addTextBtn.addEventListener("click", () => {
    const qid = `Q${builderQuestions.length + 1}`;
    builderQuestions.push({
      QuestionID: qid,
      QuestionText: "",
      ImageURL: "",
      Type: "Text",
      Options: [],
      CorrectAnswer: "",
      MarksCorrect: 4.0,
      MarksNegative: 0.0
    });
    renderBuilderQuestions();
  });

  function renderBuilderQuestions() {
    questionsBuilderList.innerHTML = "";
    questionCountLabel.textContent = builderQuestions.length;

    builderQuestions.forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "q-editor-card";

      const header = document.createElement("div");
      header.className = "q-editor-header";
      header.innerHTML = `
        <span class="q-editor-title">#${idx + 1} (${q.Type}) - ID: ${escapeHtml(q.QuestionID)}</span>
      `;
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "btn btn-danger";
      removeBtn.style.cssText = "font-size: 0.75rem; min-height: 28px; padding: 0.2rem 0.5rem;";
      removeBtn.textContent = "Remove";
      removeBtn.addEventListener("click", () => {
        builderQuestions.splice(idx, 1);
        renderBuilderQuestions();
      });
      header.appendChild(removeBtn);
      card.appendChild(header);

      // Question Text Input
      const textGroup = document.createElement("div");
      textGroup.className = "form-group";
      textGroup.innerHTML = `
        <label class="form-label" style="font-size: 0.85rem;">Question Text</label>
        <textarea class="form-control" rows="2" style="font-size: 0.9rem;" required></textarea>
      `;
      const textarea = textGroup.querySelector("textarea");
      textarea.value = q.QuestionText;
      textarea.addEventListener("input", (e) => { q.QuestionText = e.target.value; });
      card.appendChild(textGroup);

      // Optional Image URL
      const imgGroup = document.createElement("div");
      imgGroup.className = "form-group";
      imgGroup.innerHTML = `
        <label class="form-label" style="font-size: 0.85rem;">Image URL (Optional HTTPS)</label>
        <input type="text" class="form-control" style="font-size: 0.9rem;" placeholder="https://...">
      `;
      const imgInput = imgGroup.querySelector("input");
      imgInput.value = q.ImageURL || "";
      imgInput.addEventListener("input", (e) => { q.ImageURL = e.target.value; });
      card.appendChild(imgGroup);

      if (q.Type === "MCQ") {
        const optsContainer = document.createElement("div");
        optsContainer.style.marginBottom = "0.75rem";
        optsContainer.innerHTML = `<label class="form-label" style="font-size: 0.85rem;">Options (Select the correct answer radio)</label>`;

        q.Options.forEach((opt, optIdx) => {
          const row = document.createElement("div");
          row.style.cssText = "display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;";
          row.innerHTML = `
            <input type="radio" name="correct_${q.QuestionID}" ${q.CorrectAnswer === opt.OptionID ? 'checked' : ''} style="cursor: pointer;">
            <input type="text" class="form-control" style="font-size: 0.85rem; padding: 0.4rem;" placeholder="Option ${optIdx + 1}" required>
          `;
          const radio = row.querySelector("input[type='radio']");
          const optText = row.querySelector("input[type='text']");
          optText.value = opt.Text;

          radio.addEventListener("change", () => {
            q.CorrectAnswer = opt.OptionID;
          });
          optText.addEventListener("input", (e) => {
            opt.Text = e.target.value;
          });

          optsContainer.appendChild(row);
        });
        card.appendChild(optsContainer);

      } else if (q.Type === "Text") {
        const ansGroup = document.createElement("div");
        ansGroup.className = "form-group";
        ansGroup.innerHTML = `
          <label class="form-label" style="font-size: 0.85rem;">Correct Answer (Comma-separated acceptable variations)</label>
          <input type="text" class="form-control" style="font-size: 0.9rem;" placeholder="e.g. delhi,new delhi" required>
        `;
        const ansInput = ansGroup.querySelector("input");
        ansInput.value = q.CorrectAnswer;
        ansInput.addEventListener("input", (e) => { q.CorrectAnswer = e.target.value; });
        card.appendChild(ansGroup);
      }

      questionsBuilderList.appendChild(card);
    });
  }

  // Save Paper (Create or Update)
  paperEditorForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    editorError.style.display = "none";

    if (builderQuestions.length === 0) {
      editorError.textContent = "Please add at least one question before saving.";
      editorError.style.display = "block";
      return;
    }

    const title = paperTitleInput.value.trim();
    const priceRupees = parseInt(paperPriceInput.value, 10) || 0;
    const priceMinorUnits = priceRupees * 100;
    const timeLimitMinutes = parseInt(paperTimeInput.value, 10) || 20;

    const payload = {
      Title: title,
      PriceMinorUnits: priceMinorUnits,
      Currency: "INR",
      TimeLimitMinutes: timeLimitMinutes,
      NegativeMarkingEnabled: negMarkingCheckbox.checked,
      ShowAnswerKey: showAnswerKeyCheckbox.checked,
      AllowResume: true,
      AntiCheatPolicy: antiCheatSelect.value,
      Questions: builderQuestions
    };

    try {
      if (editingPaperId) {
        await API.put(`/admin/paper/${editingPaperId}`, payload, Auth.getAdminHeaders());
      } else {
        await API.post("/admin/create-paper", payload, Auth.getAdminHeaders());
      }

      if (typeof paperEditorModal.close === "function") paperEditorModal.close();
      loadPapers();
    } catch (err) {
      editorError.textContent = err.message || "Failed to save paper.";
      editorError.style.display = "block";
    }
  });

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
});

