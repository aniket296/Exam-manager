// Storefront Logic
document.addEventListener("DOMContentLoaded", () => {
  const testsGrid = document.getElementById("testsGrid");
  const statusAlert = document.getElementById("statusAlert");
  const checkoutModal = document.getElementById("checkoutModal");
  const checkoutForm = document.getElementById("checkoutForm");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const cancelModalBtn = document.getElementById("cancelModalBtn");
  const payBtn = document.getElementById("payBtn");
  const checkoutError = document.getElementById("checkoutError");

  let currentPaper = null;

  function formatPrice(minorUnits, currency) {
    if (!minorUnits || minorUnits === 0) return "Free";
    const amount = (minorUnits / 100).toFixed(minorUnits % 100 === 0 ? 0 : 2);
    return currency === "INR" ? `₹${amount}` : `${amount} ${currency}`;
  }

  // Load published assessment papers
  async function loadPublishedPapers() {
    try {
      const papers = await API.get("/papers");
      testsGrid.innerHTML = "";

      if (!papers || papers.length === 0) {
        testsGrid.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📚</div>
            <h3 style="font-size: 1.25rem; font-weight: 700;">No Tests Available Right Now</h3>
            <p style="color: var(--text-muted); margin-top: 0.25rem;">Please check back soon for upcoming tests.</p>
          </div>
        `;
        return;
      }

      papers.forEach(paper => {
        const card = document.createElement("div");
        card.className = "test-card";

        const header = document.createElement("div");
        header.className = "test-card-header";

        const title = document.createElement("h3");
        title.className = "test-card-title";
        title.textContent = paper.Title; // Safe text rendering (XSS protection)

        const meta = document.createElement("div");
        meta.className = "test-meta";

        const timePill = document.createElement("span");
        timePill.className = "meta-pill pill-time";
        timePill.textContent = `⏱️ ${paper.TimeLimitMinutes} Mins`;

        const qPill = document.createElement("span");
        qPill.className = "meta-pill";
        qPill.textContent = `📝 ${paper.QuestionCount} Questions`;

        meta.appendChild(timePill);
        meta.appendChild(qPill);

        if (paper.NegativeMarkingEnabled) {
          const negPill = document.createElement("span");
          negPill.className = "meta-pill pill-penalty";
          negPill.textContent = `⚠️ Negative Marking`;
          meta.appendChild(negPill);
        }

        header.appendChild(title);
        header.appendChild(meta);

        const footer = document.createElement("div");
        footer.className = "test-card-footer";

        const priceTag = document.createElement("div");
        priceTag.className = "price-tag";

        const priceLabel = document.createElement("span");
        priceLabel.className = "price-label";
        priceLabel.textContent = "Fee";

        const priceVal = document.createElement("span");
        priceVal.className = "price-val";
        priceVal.textContent = formatPrice(paper.PriceMinorUnits, paper.Currency);

        priceTag.appendChild(priceLabel);
        priceTag.appendChild(priceVal);

        const selectBtn = document.createElement("button");
        selectBtn.className = "btn btn-primary";
        selectBtn.textContent = "Select Test";
        selectBtn.setAttribute("aria-label", `Select test: ${paper.Title}`);
        selectBtn.addEventListener("click", () => openCheckout(paper));

        footer.appendChild(priceTag);
        footer.appendChild(selectBtn);

        card.appendChild(header);
        card.appendChild(footer);
        testsGrid.appendChild(card);
      });
    } catch (err) {
      testsGrid.innerHTML = "";
      statusAlert.style.display = "block";
      statusAlert.className = "alert alert-danger";
      statusAlert.textContent = err.message || "Failed to load tests. Please refresh.";
    }
  }

  function openCheckout(paper) {
    currentPaper = paper;
    document.getElementById("selectedTestTitle").value = paper.Title;
    document.getElementById("selectedTestTime").textContent = `${paper.TimeLimitMinutes} Minutes`;
    checkoutError.style.display = "none";
    checkoutForm.reset();
    document.getElementById("selectedTestTitle").value = paper.Title;

    if (typeof checkoutModal.showModal === "function") {
      checkoutModal.showModal();
    } else {
      checkoutModal.setAttribute("open", "true");
    }
  }

  function closeCheckout() {
    if (typeof checkoutModal.close === "function") {
      checkoutModal.close();
    } else {
      checkoutModal.removeAttribute("open");
    }
  }

  closeModalBtn.addEventListener("click", closeCheckout);
  cancelModalBtn.addEventListener("click", closeCheckout);

  // Handle Form Submission with Access PIN
  checkoutForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentPaper) return;

    const studentName = document.getElementById("studentName").value.trim();
    const contact = document.getElementById("contactInfo").value.trim();
    const accessPin = document.getElementById("accessPin").value.trim();

    if (!studentName || !contact || !accessPin) {
      checkoutError.textContent = "Please fill in all required fields (Name, Phone, and Access PIN).";
      checkoutError.style.display = "block";
      return;
    }

    payBtn.disabled = true;
    payBtn.textContent = "Verifying Access PIN...";
    checkoutError.style.display = "none";

    try {
      // Verify Access PIN on backend
      const res = await API.post("/payments/verify-pin", {
        paper_id: currentPaper.PaperID,
        name: studentName,
        phone: contact,
        pin: accessPin
      });

      // Store attempt session securely
      Auth.setAttemptSession(
        res.AttemptToken || res.attempt_token,
        res.AttemptID || res.attempt_id,
        studentName,
        currentPaper.PaperID
      );

      closeCheckout();
      // Seamless redirect to test room
      window.location.href = "exam.html";
    } catch (err) {
      checkoutError.textContent = err.message || "Invalid Access PIN. Please try again.";
      checkoutError.style.display = "block";
      payBtn.disabled = false;
      payBtn.textContent = "Verify PIN & Start Test 🚀";
    }
  });

  loadPublishedPapers();
});

