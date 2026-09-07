// Result Page Controller & jsPDF Report Card Generator
document.addEventListener("DOMContentLoaded", () => {
  const rawData = sessionStorage.getItem("last_exam_result");
  const resultCard = document.getElementById("resultCard");

  if (!rawData) {
    resultCard.innerHTML = `
      <div style="font-size: 3rem; margin-bottom: 0.5rem;">📄</div>
      <h2>No Test Result Found</h2>
      <p style="color: var(--text-muted); margin: 1rem 0 1.5rem 0;">
        Please complete an assessment to view your report card.
      </p>
      <a href="index.html" class="btn btn-primary btn-lg">Browse Available Tests</a>
    `;
    return;
  }

  const result = JSON.parse(rawData);

  // Populate Scorecard
  document.getElementById("studentNameDisplay").textContent = `Great work, ${result.StudentName}!`;
  document.getElementById("paperTitleDisplay").textContent = result.PaperTitle;
  document.getElementById("scoreDisplay").textContent = result.Score;
  document.getElementById("maxMarksDisplay").textContent = `out of ${result.MaxMarks} marks`;
  document.getElementById("percentageDisplay").textContent = `${result.Percentage}% Score`;

  document.getElementById("correctCountDisplay").textContent = result.CorrectCount;
  document.getElementById("wrongCountDisplay").textContent = result.WrongCount;
  document.getElementById("skippedCountDisplay").textContent = result.UnansweredCount;

  // Breakdown rendering
  const breakdownSection = document.getElementById("breakdownSection");
  const breakdownList = document.getElementById("breakdownList");

  if (result.QuestionBreakdown && result.QuestionBreakdown.length > 0) {
    breakdownSection.style.display = "block";
    breakdownList.innerHTML = "";

    result.QuestionBreakdown.forEach((item, idx) => {
      const box = document.createElement("div");
      box.className = `breakdown-item ${
        !item.StudentAnswer ? "unanswered" : (item.IsCorrect ? "correct" : "wrong")
      }`;

      const title = document.createElement("div");
      title.className = "breakdown-q-title";
      title.textContent = `Q${idx + 1}. ${item.QuestionText}`;

      const answersBox = document.createElement("div");
      answersBox.className = "breakdown-answers";

      const studentLine = document.createElement("div");
      studentLine.className = "ans-line";
      studentLine.innerHTML = `
        <span class="ans-label">Your Answer:</span>
        <span style="font-weight: 600;">${item.StudentAnswer ? escapeHtml(item.StudentAnswer) : "<em>Unanswered</em>"}</span>
      `;

      answersBox.appendChild(studentLine);

      // Only show correct answer if paper's ShowAnswerKey permits it (Section 47)
      if (result.ShowAnswerKey && item.CorrectAnswer) {
        const correctLine = document.createElement("div");
        correctLine.className = "ans-line";
        correctLine.innerHTML = `
          <span class="ans-label" style="color: #059669;">Correct Answer:</span>
          <span style="font-weight: 700; color: #059669;">${escapeHtml(item.CorrectAnswer)}</span>
        `;
        answersBox.appendChild(correctLine);
      }

      box.appendChild(title);
      box.appendChild(answersBox);
      breakdownList.appendChild(box);
    });
  }

  // jsPDF Report Card Generator (Section 48)
  const downloadPdfBtn = document.getElementById("downloadPdfBtn");
  downloadPdfBtn.addEventListener("click", () => {
    generatePdfReport(result);
  });

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function generatePdfReport(resData) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Primary Header Banner
    doc.setFillColor(79, 70, 229); // Primary Indigo
    doc.rect(0, 0, 210, 36, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.text("SMARTASSESS JUNIOR", 105, 16, { align: "center" });

    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    doc.text("OFFICIAL ASSESSMENT REPORT CARD", 105, 26, { align: "center" });

    // Student & Test Information
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.text("Student Name:", 16, 48);
    doc.setFont("helvetica", "normal");
    doc.text(resData.StudentName, 55, 48);

    doc.setFont("helvetica", "bold");
    doc.text("Assessment Title:", 16, 56);
    doc.setFont("helvetica", "normal");
    doc.text(resData.PaperTitle, 55, 56);

    doc.setFont("helvetica", "bold");
    doc.text("Completed On:", 16, 64);
    doc.setFont("helvetica", "normal");
    const dateStr = resData.CompletedAt ? new Date(resData.CompletedAt).toLocaleString() : new Date().toLocaleString();
    doc.text(dateStr, 55, 64);

    // Divider
    doc.setDrawColor(226, 232, 240);
    doc.line(16, 70, 194, 70);

    // Score Summary Box
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(16, 76, 178, 38, 3, 3, "F");
    doc.rect(16, 76, 178, 38, "S");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.setTextColor(79, 70, 229);
    doc.text(`Total Score: ${resData.Score} / ${resData.MaxMarks}`, 24, 88);

    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text(`Overall Percentage: ${resData.Percentage}%`, 24, 98);

    doc.setFontSize(10);
    doc.setTextColor(100, 116, 139);
    doc.text(
      `Correct: ${resData.CorrectCount}    |    Incorrect: ${resData.WrongCount}    |    Unanswered: ${resData.UnansweredCount}`,
      24,
      106
    );

    // Question Breakdown Summary
    let y = 126;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    doc.text("Question-Wise Summary:", 16, y);
    y += 8;

    if (resData.QuestionBreakdown) {
      doc.setFontSize(9);
      resData.QuestionBreakdown.forEach((q, i) => {
        if (y > 270) {
          doc.addPage();
          y = 20;
        }

        const statusText = !q.StudentAnswer
          ? "Unanswered"
          : (q.IsCorrect ? "Correct (+ marks awarded)" : "Incorrect");
        const statusColor = !q.StudentAnswer
          ? [100, 116, 139]
          : (q.IsCorrect ? [16, 185, 129] : [239, 68, 68]);

        doc.setFont("helvetica", "bold");
        doc.setTextColor(30, 41, 59);
        doc.text(`Q${i + 1}. ${q.QuestionText.substring(0, 80)}${q.QuestionText.length > 80 ? '...' : ''}`, 16, y);
        y += 5;

        doc.setFont("helvetica", "normal");
        doc.setTextColor(statusColor[0], statusColor[1], statusColor[2]);
        doc.text(`Result: ${statusText} | Student Ans: ${q.StudentAnswer || 'None'}`, 20, y);
        y += 7;
      });
    }

    // Informational disclaimer (Section 48)
    doc.setFontSize(8);
    doc.setTextColor(148, 163, 184);
    doc.text(
      "Notice: This client-generated report card is for personal/school review and is not an official government certificate.",
      105,
      285,
      { align: "center" }
    );

    // Save PDF
    const safeName = resData.StudentName.replace(/[^a-zA-Z0-9]/g, "_");
    doc.save(`ReportCard_${safeName}.pdf`);
  }
});

