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

          const delBtn = document.createElement("button");
          delBtn.className = "btn btn-danger";
          delBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          delBtn.textContent = "🗑 Delete";
          delBtn.addEventListener("click", () => handleDelete(p.PaperID, p.Title));
          tdActions.appendChild(delBtn);

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

          const delBtn = document.createElement("button");
          delBtn.className = "btn btn-danger";
          delBtn.style.cssText = "font-size: 0.8rem; min-height: 32px; padding: 0.3rem 0.6rem;";
          delBtn.textContent = "🗑 Delete";
          delBtn.addEventListener("click", () => handleDelete(p.PaperID, p.Title));
          tdActions.appendChild(delBtn);
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

  async function handleDelete(paperId, paperTitle) {
    if (!confirm(`⚠️ Permanently delete "${paperTitle}"?\n\nThis cannot be undone. Active attempts will block deletion.`)) return;
    try {
      await API.delete(`/admin/papers/${paperId}`, Auth.getAdminHeaders());
      loadPapers();
    } catch (err) {
      alert(err.message || "Delete failed. The paper may have active attempts — archive it instead.");
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
    const qid = `Q${Date.now()}`;
    builderQuestions.push({
      QuestionID: qid,
      QuestionText: "",
      image: null,
      ImageURL: "",
      Type: "MCQ",
      Options: [
        { OptionID: "OPT1", Text: "", image: null },
        { OptionID: "OPT2", Text: "", image: null },
        { OptionID: "OPT3", Text: "", image: null },
        { OptionID: "OPT4", Text: "", image: null }
      ],
      CorrectAnswer: "OPT1",
      MarksCorrect: 4.0,
      MarksNegative: 1.0
    });
    renderBuilderQuestions();
    // Scroll to newly added card
    setTimeout(() => {
      const cards = questionsBuilderList.querySelectorAll(".q-editor-card");
      if (cards.length) cards[cards.length - 1].scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 50);
  });

  addTextBtn.addEventListener("click", () => {
    const qid = `Q${Date.now()}`;
    builderQuestions.push({
      QuestionID: qid,
      QuestionText: "",
      image: null,
      ImageURL: "",
      Type: "Text",
      Options: [],
      CorrectAnswer: "",
      MarksCorrect: 4.0,
      MarksNegative: 0.0
    });
    renderBuilderQuestions();
    setTimeout(() => {
      const cards = questionsBuilderList.querySelectorAll(".q-editor-card");
      if (cards.length) cards[cards.length - 1].scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 50);
  });

  // ── File → Base64 helper ──────────────────────────────────────────────────
  function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = () => reject(new Error("Failed to read image"));
      reader.readAsDataURL(file);
    });
  }

  // ── Image picker widget factory ───────────────────────────────────────────
  function makeImagePicker(labelText, currentBase64, onUpdate) {
    const wrap = document.createElement("div");
    wrap.className = "img-picker-wrap";

    const label = document.createElement("span");
    label.className = "img-picker-label";
    label.textContent = labelText;
    wrap.appendChild(label);

    const preview = document.createElement("img");
    preview.className = "img-preview";
    if (currentBase64) {
      preview.src = currentBase64;
      preview.style.display = "block";
    } else {
      preview.style.display = "none";
    }
    wrap.appendChild(preview);

    const actionsRow = document.createElement("div");
    actionsRow.className = "img-picker-actions";

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/*";
    fileInput.style.display = "none";

    const chooseBtn = document.createElement("button");
    chooseBtn.type = "button";
    chooseBtn.className = "btn btn-secondary opt-img-btn";
    chooseBtn.textContent = currentBase64 ? "📷 Change" : "📷 Add Image";
    chooseBtn.addEventListener("click", () => fileInput.click());

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-danger opt-img-btn";
    removeBtn.textContent = "✕ Remove";
    removeBtn.style.display = currentBase64 ? "inline-flex" : "none";
    removeBtn.addEventListener("click", () => {
      preview.src = "";
      preview.style.display = "none";
      chooseBtn.textContent = "📷 Add Image";
      removeBtn.style.display = "none";
      onUpdate(null);
    });

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      if (file.size > 2 * 1024 * 1024) {
        alert("Image is too large. Please use an image under 2 MB.");
        return;
      }
      try {
        const b64 = await readFileAsBase64(file);
        preview.src = b64;
        preview.style.display = "block";
        chooseBtn.textContent = "📷 Change";
        removeBtn.style.display = "inline-flex";
        onUpdate(b64);
      } catch (e) {
        alert("Could not read image file.");
      }
    });

    actionsRow.appendChild(fileInput);
    actionsRow.appendChild(chooseBtn);
    actionsRow.appendChild(removeBtn);
    wrap.appendChild(actionsRow);
    return wrap;
  }

  // ── Main builder renderer ─────────────────────────────────────────────────
  function renderBuilderQuestions() {
    questionsBuilderList.innerHTML = "";
    questionCountLabel.textContent = builderQuestions.length;

    builderQuestions.forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "q-editor-card";

      // ── Header ─────────────────────────────────────────
      const header = document.createElement("div");
      header.className = "q-editor-header";

      const titleSpan = document.createElement("span");
      titleSpan.className = "q-editor-title";
      titleSpan.textContent = `#${idx + 1} ${q.Type}`;
      header.appendChild(titleSpan);

      const controls = document.createElement("div");
      controls.className = "q-editor-controls";

      // Move Up
      if (idx > 0) {
        const upBtn = document.createElement("button");
        upBtn.type = "button";
        upBtn.className = "btn btn-secondary";
        upBtn.style.cssText = "font-size: 0.75rem; min-height: 28px; padding: 0.2rem 0.5rem;";
        upBtn.title = "Move Up";
        upBtn.textContent = "▲";
        upBtn.addEventListener("click", () => {
          [builderQuestions[idx - 1], builderQuestions[idx]] = [builderQuestions[idx], builderQuestions[idx - 1]];
          renderBuilderQuestions();
        });
        controls.appendChild(upBtn);
      }

      // Move Down
      if (idx < builderQuestions.length - 1) {
        const downBtn = document.createElement("button");
        downBtn.type = "button";
        downBtn.className = "btn btn-secondary";
        downBtn.style.cssText = "font-size: 0.75rem; min-height: 28px; padding: 0.2rem 0.5rem;";
        downBtn.title = "Move Down";
        downBtn.textContent = "▼";
        downBtn.addEventListener("click", () => {
          [builderQuestions[idx], builderQuestions[idx + 1]] = [builderQuestions[idx + 1], builderQuestions[idx]];
          renderBuilderQuestions();
        });
        controls.appendChild(downBtn);
      }

      // Duplicate
      const dupBtn = document.createElement("button");
      dupBtn.type = "button";
      dupBtn.className = "btn btn-secondary";
      dupBtn.style.cssText = "font-size: 0.75rem; min-height: 28px; padding: 0.2rem 0.5rem;";
      dupBtn.textContent = "⧉ Duplicate";
      dupBtn.addEventListener("click", () => {
        const clone = JSON.parse(JSON.stringify(q));
        clone.QuestionID = `Q${Date.now()}`;
        builderQuestions.splice(idx + 1, 0, clone);
        renderBuilderQuestions();
      });
      controls.appendChild(dupBtn);

      // Remove
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "btn btn-danger";
      removeBtn.style.cssText = "font-size: 0.75rem; min-height: 28px; padding: 0.2rem 0.5rem;";
      removeBtn.textContent = "✕ Remove";
      removeBtn.addEventListener("click", () => {
        builderQuestions.splice(idx, 1);
        renderBuilderQuestions();
      });
      controls.appendChild(removeBtn);

      header.appendChild(controls);
      card.appendChild(header);

      // ── Marks row ───────────────────────────────────────
      const marksRow = document.createElement("div");
      marksRow.className = "q-editor-marks-row";

      const marksCorrectGroup = document.createElement("div");
      marksCorrectGroup.className = "form-group";
      marksCorrectGroup.innerHTML = `<label class="form-label" style="font-size:0.8rem;">✅ Marks (Correct)</label>`;
      const marksCorrectInput = document.createElement("input");
      marksCorrectInput.type = "number";
      marksCorrectInput.className = "form-control";
      marksCorrectInput.style.fontSize = "0.9rem";
      marksCorrectInput.min = "0";
      marksCorrectInput.step = "0.5";
      marksCorrectInput.value = q.MarksCorrect;
      marksCorrectInput.addEventListener("input", (e) => { q.MarksCorrect = parseFloat(e.target.value) || 0; });
      marksCorrectGroup.appendChild(marksCorrectInput);
      marksRow.appendChild(marksCorrectGroup);

      const marksNegGroup = document.createElement("div");
      marksNegGroup.className = "form-group";
      marksNegGroup.innerHTML = `<label class="form-label" style="font-size:0.8rem;">❌ Deduction (Wrong)</label>`;
      const marksNegInput = document.createElement("input");
      marksNegInput.type = "number";
      marksNegInput.className = "form-control";
      marksNegInput.style.fontSize = "0.9rem";
      marksNegInput.min = "0";
      marksNegInput.step = "0.5";
      marksNegInput.value = q.MarksNegative;
      marksNegInput.addEventListener("input", (e) => { q.MarksNegative = parseFloat(e.target.value) || 0; });
      marksNegGroup.appendChild(marksNegInput);
      marksRow.appendChild(marksNegGroup);

      card.appendChild(marksRow);

      // ── Question Text ───────────────────────────────────
      const textGroup = document.createElement("div");
      textGroup.className = "form-group";
      textGroup.innerHTML = `<label class="form-label" style="font-size: 0.85rem;">Question Text <span style="color:var(--danger)">*</span></label>`;
      const textarea = document.createElement("textarea");
      textarea.className = "form-control";
      textarea.rows = 2;
      textarea.style.fontSize = "0.9rem";
      textarea.required = true;
      textarea.placeholder = "Type your question here…";
      textarea.value = q.QuestionText;
      textarea.addEventListener("input", (e) => { q.QuestionText = e.target.value; });
      textGroup.appendChild(textarea);
      card.appendChild(textGroup);

      // ── Question Image Picker ───────────────────────────
      const qImgPicker = makeImagePicker(
        "📷 Question Image (optional, stored as Base64)",
        q.image || (q.ImageURL && q.ImageURL.startsWith("data:") ? q.ImageURL : null),
        (b64) => { q.image = b64; }
      );
      card.appendChild(qImgPicker);

      // ── MCQ Options ─────────────────────────────────────
      if (q.Type === "MCQ") {
        const optsLabel = document.createElement("label");
        optsLabel.className = "form-label";
        optsLabel.style.fontSize = "0.85rem";
        optsLabel.textContent = "Options — select the radio button for the correct answer";
        card.appendChild(optsLabel);

        q.Options.forEach((opt, optIdx) => {
          const row = document.createElement("div");
          row.className = "opt-row";

          // Radio button
          const radio = document.createElement("input");
          radio.type = "radio";
          radio.name = `correct_${q.QuestionID}`;
          radio.checked = q.CorrectAnswer === opt.OptionID;
          radio.title = "Mark as correct answer";
          radio.style.cssText = "cursor: pointer; width: 18px; height: 18px; flex-shrink: 0;";
          radio.addEventListener("change", () => { q.CorrectAnswer = opt.OptionID; });
          row.appendChild(radio);

          // Option text
          const optText = document.createElement("input");
          optText.type = "text";
          optText.className = "form-control";
          optText.style.cssText = "font-size: 0.85rem; padding: 0.4rem; flex: 1; min-width: 120px;";
          optText.placeholder = `Option ${optIdx + 1}`;
          optText.value = opt.Text;
          optText.addEventListener("input", (e) => { opt.Text = e.target.value; });
          row.appendChild(optText);

          // Option image thumbnail (if already has one)
          if (opt.image) {
            const thumb = document.createElement("img");
            thumb.className = "opt-img-thumb";
            thumb.src = opt.image;
            thumb.title = "Click to change image";
            row.appendChild(thumb);
          }

          // Option image picker button
          const optFileInput = document.createElement("input");
          optFileInput.type = "file";
          optFileInput.accept = "image/*";
          optFileInput.style.display = "none";
          row.appendChild(optFileInput);

          const optImgBtn = document.createElement("button");
          optImgBtn.type = "button";
          optImgBtn.className = "btn btn-secondary opt-img-btn";
          optImgBtn.textContent = opt.image ? "🖼 Change" : "🖼 Image";
          optImgBtn.title = "Add/change image for this option";
          optImgBtn.addEventListener("click", () => optFileInput.click());
          row.appendChild(optImgBtn);

          optFileInput.addEventListener("change", async () => {
            const file = optFileInput.files[0];
            if (!file) return;
            if (file.size > 1 * 1024 * 1024) {
              alert("Option image is too large. Please use an image under 1 MB.");
              return;
            }
            try {
              const b64 = await readFileAsBase64(file);
              opt.image = b64;
              renderBuilderQuestions(); // Re-render to show thumbnail
            } catch (e) {
              alert("Could not read image file.");
            }
          });

          // Remove option image
          if (opt.image) {
            const optRemoveBtn = document.createElement("button");
            optRemoveBtn.type = "button";
            optRemoveBtn.className = "btn btn-danger opt-img-btn";
            optRemoveBtn.textContent = "✕";
            optRemoveBtn.title = "Remove option image";
            optRemoveBtn.addEventListener("click", () => {
              opt.image = null;
              renderBuilderQuestions();
            });
            row.appendChild(optRemoveBtn);
          }

          card.appendChild(row);
        });

      } else if (q.Type === "Text") {
        const ansGroup = document.createElement("div");
        ansGroup.className = "form-group";
        ansGroup.innerHTML = `<label class="form-label" style="font-size: 0.85rem;">Correct Answer <small style="color:var(--text-muted)">(comma-separated acceptable variations)</small></label>`;
        const ansInput = document.createElement("input");
        ansInput.type = "text";
        ansInput.className = "form-control";
        ansInput.style.fontSize = "0.9rem";
        ansInput.placeholder = "e.g. delhi,new delhi";
        ansInput.required = true;
        ansInput.value = q.CorrectAnswer;
        ansInput.addEventListener("input", (e) => { q.CorrectAnswer = e.target.value; });
        ansGroup.appendChild(ansInput);
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

