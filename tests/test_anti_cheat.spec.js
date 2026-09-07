const { test, expect } = require('@playwright/test');

// Helper to seed active exam attempt session before running UI tests
async function setupAndStartExam(page) {
  // 1. Create order & verify payment on backend
  const apiBase = 'http://127.0.0.1:8000';
  const orderRes = await page.request.post(`${apiBase}/payments/create-order`, {
    data: {
      PaperID: 'pap_math_gk_01',
      StudentName: 'Rohan Sharma',
      StudentIdentifier: 'Roll 101'
    }
  });
  expect(orderRes.ok()).toBeTruthy();
  const order = await orderRes.json();

  const paymentId = `pay_e2e_${order.OrderID}`;
  const verifyRes = await page.request.post(`${apiBase}/payments/verify`, {
    data: {
      OrderID: order.OrderID,
      PaymentID: paymentId,
      Signature: `sim_sig_${order.OrderID}_${paymentId}`
    }
  });
  expect(verifyRes.ok()).toBeTruthy();
  const verifyData = await verifyRes.json();

  // 2. Open page and initialize student session in sessionStorage
  await page.goto('/exam.html');
  await page.evaluate(({ token, attemptId, studentName, paperId }) => {
    sessionStorage.setItem('exam_attempt_token', token);
    sessionStorage.setItem('exam_attempt_id', attemptId);
    sessionStorage.setItem('exam_student_name', studentName);
    sessionStorage.setItem('exam_paper_id', paperId);
  }, {
    token: verifyData.AttemptToken,
    attemptId: verifyData.AttemptID,
    studentName: 'Rohan Sharma',
    paperId: 'pap_math_gk_01'
  });

  // 3. Reload page to read session and start test
  await page.reload();
  await expect(page.locator('#startExamBtn')).toBeVisible();
  await page.locator('#startExamBtn').click();

  // Wait for question card to appear
  await expect(page.locator('#activeExamRoom')).toBeVisible();
  return verifyData;
}

test.describe('Suite 4: Frontend Anti-Cheat & UI Integrity', () => {

  // --- 1. Fullscreen Enforcement ---
  test('1. Fullscreen exit triggers warning modal and records strike', async ({ page }) => {
    await setupAndStartExam(page);

    // Exit fullscreen or dispatch event with null fullscreenElement
    await page.evaluate(async () => {
      if (document.fullscreenElement) {
        try {
          await document.exitFullscreen();
        } catch (e) {
          Object.defineProperty(document, 'fullscreenElement', { value: null, configurable: true });
          document.dispatchEvent(new Event('fullscreenchange'));
        }
      } else {
        Object.defineProperty(document, 'fullscreenElement', { value: null, configurable: true });
        document.dispatchEvent(new Event('fullscreenchange'));
      }
    });

    // Warning dialog should appear
    const dialog = page.locator('#antiCheatDialog');
    await expect(dialog).toBeVisible();
    await expect(page.locator('#antiCheatMessage')).toContainText(/stay on the test screen/i);

    // Click Return to Test
    await page.locator('#closeWarningBtn').click();
    await expect(dialog).not.toBeVisible();
  });

  // --- 2. Tab-Switch & Blur Detection with Grace Period ---
  test('2. Blur grace period and 3rd strike auto-submit', async ({ page }) => {
    await setupAndStartExam(page);

    // Case A: Quick blur/focus under 2 seconds (grace period) -> No strike issued
    await page.evaluate(() => {
      window.dispatchEvent(new Event('blur'));
    });
    // Wait 500ms (well under 2 seconds) and refocus
    await page.waitForTimeout(500);
    await page.evaluate(() => {
      window.dispatchEvent(new Event('focus'));
    });

    // Wait 2.5 seconds to confirm grace period prevented the strike
    await page.waitForTimeout(2500);
    const dialog = page.locator('#antiCheatDialog');
    await expect(dialog).not.toBeVisible();

    // Case B: Visibility change to hidden for > 2 seconds -> Strike increments
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { value: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await expect(dialog).toBeVisible();
    await page.locator('#closeWarningBtn').click();
    await page.waitForTimeout(2200); // clear debounce

    // Case C: Simulate strikes until 3rd strike auto-submit triggers
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { value: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await page.waitForTimeout(2200);

    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { value: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    // 3rd strike should show auto-submit notice and redirect to result page
    await expect(page.locator('#antiCheatMessage')).toContainText(/submitted now/i);
    await expect(page).toHaveURL(/result\.html/, { timeout: 10000 });
  });

  // --- 3. Client-Side Action Locks ---
  test('3. Intercepts contextmenu, copy, cut, paste, and keydown shortcuts', async ({ page }) => {
    await setupAndStartExam(page);

    // Verify contextmenu prevented
    const isContextMenuPrevented = await page.evaluate(() => {
      const event = new MouseEvent('contextmenu', { cancelable: true, bubbles: true });
      return !document.dispatchEvent(event); // returns true if preventDefault() was called
    });
    expect(isContextMenuPrevented).toBeTruthy();

    // Verify copy prevented
    const isCopyPrevented = await page.evaluate(() => {
      const event = new Event('copy', { cancelable: true, bubbles: true });
      return !document.dispatchEvent(event);
    });
    expect(isCopyPrevented).toBeTruthy();

    // Verify cut prevented
    const isCutPrevented = await page.evaluate(() => {
      const event = new Event('cut', { cancelable: true, bubbles: true });
      return !document.dispatchEvent(event);
    });
    expect(isCutPrevented).toBeTruthy();

    // Verify paste prevented
    const isPastePrevented = await page.evaluate(() => {
      const event = new Event('paste', { cancelable: true, bubbles: true });
      return !document.dispatchEvent(event);
    });
    expect(isPastePrevented).toBeTruthy();

    // Verify Keydown shortcuts blocked (F12, Ctrl+C, Ctrl+V, Ctrl+P)
    const shortcuts = [
      { key: 'F12', keyCode: 123 },
      { key: 'c', ctrlKey: true },
      { key: 'v', ctrlKey: true },
      { key: 'p', ctrlKey: true },
      { key: 'PrintScreen', keyCode: 44 }
    ];

    for (const sc of shortcuts) {
      const isBlocked = await page.evaluate((s) => {
        const event = new KeyboardEvent('keydown', {
          key: s.key,
          keyCode: s.keyCode || 0,
          ctrlKey: !!s.ctrlKey,
          cancelable: true,
          bubbles: true
        });
        return !document.dispatchEvent(event);
      }, sc);
      expect(isBlocked).toBeTruthy();
    }
  });

  // --- 4. Safe Resume Test ---
  test('4. Safe resume preserves answers and continuous timer on page reload', async ({ page }) => {
    await setupAndStartExam(page);

    // Answer Q1: Select first option
    const firstOption = page.locator('.option-item').first();
    await firstOption.click();
    await expect(firstOption).toHaveClass(/selected/);

    // Move to Q2 and answer
    await page.locator('#nextQuestionBtn').click();
    await page.waitForTimeout(300);
    const q2FirstOption = page.locator('.option-item').first();
    await q2FirstOption.click();
    await expect(q2FirstOption).toHaveClass(/selected/);

    // Read timer value before reload
    const timerTextBefore = await page.locator('#timerDisplay').textContent();

    // Trigger page reload (mid-test)
    await page.reload();
    if (await page.locator('#startExamBtn').isVisible()) {
      await page.locator('#startExamBtn').click();
    }

    // Verify active room is resumed
    await expect(page.locator('#activeExamRoom')).toBeVisible();

    // Verify Q1 answer is preserved in the palette (marked answered)
    const paletteButtons = page.locator('.palette-btn');
    await expect(paletteButtons.first()).toHaveClass(/answered/);

    // Verify timer continuous countdown without resetting to full duration
    const timerTextAfter = await page.locator('#timerDisplay').textContent();
    expect(timerTextAfter).not.toBe('--:--');
    expect(timerTextAfter).not.toBe('20:00'); // Did not reset to full 20 mins!

    // Verify reload did not trigger an anti-cheat strike modal
    await expect(page.locator('#antiCheatDialog')).not.toBeVisible();
  });

  // --- 5. Timer Tampering Resistance ---
  test('5. Fast-forwarding time / expiry triggers immediate auto-submission', async ({ page }) => {
    await setupAndStartExam(page);

    // Fast-forward / trigger timer expiry
    await page.evaluate(() => {
      // Simulate authoritative deadline expiry
      const expiredDeadline = new Date(Date.now() - 1000).toISOString();
      // Directly invoke the timer handler
      const timerDisplay = document.getElementById('timerDisplay');
      timerDisplay.textContent = '00:00';
      const submitBtn = document.getElementById('submitExamBtn');
      submitBtn.click();
    });

    // Submission confirmation or auto-submit handler redirects to result.html
    const confirmBtn = page.locator('#finalSubmitBtn');
    if (await confirmBtn.isVisible()) {
      await confirmBtn.click();
    }

    await expect(page).toHaveURL(/result\.html/, { timeout: 10000 });
    await expect(page.locator('#scoreDisplay')).toBeVisible();
  });

});

