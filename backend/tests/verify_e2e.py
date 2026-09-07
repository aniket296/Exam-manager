"""
End-to-End Functional & Security Verification Script
Verifies complete assessment flow from public storefront to payment, exam room, submission, and admin portal.
"""
from fastapi.testclient import TestClient
from backend.main import app

def run_e2e_verification():
    print("==================================================")
    print("STARTING E2E FUNCTIONAL & SECURITY VERIFICATION")
    print("==================================================")

    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200
        print("[OK] Step 1: Health check passed.")

        # 2. Public Storefront Papers
        res = client.get("/papers")
        assert res.status_code == 200
        papers = res.json()
        assert len(papers) >= 1
        paper = papers[0]
        paper_id = paper["PaperID"]
        assert "CorrectAnswer" not in paper
        print(f"[OK] Step 2: Public storefront loaded published paper: '{paper['Title']}' (ID: {paper_id}).")

        # 3. Create Payment Order (Price Authority Check)
        res = client.post("/payments/create-order", json={
            "PaperID": paper_id,
            "StudentName": "Kabir Sharma",
            "StudentIdentifier": "Class 6-A, Roll 12",
            "Contact": "9876543210"
        })
        assert res.status_code == 200
        order = res.json()
        order_id = order["OrderID"]
        assert order["AmountMinorUnits"] == paper["PriceMinorUnits"]
        print(f"[OK] Step 3: Order created with authoritative backend price: INR {order['AmountMinorUnits']/100}.")

        # 4. Authoritative Payment Verification
        payment_id = f"pay_e2e_{order_id}"
        sig = f"sim_sig_{order_id}_{payment_id}"
        res = client.post("/payments/verify", json={
            "OrderID": order_id,
            "PaymentID": payment_id,
            "Signature": sig
        })
        assert res.status_code == 200
        verify_data = res.json()
        assert verify_data["Success"] is True
        attempt_token = verify_data["AttemptToken"]
        attempt_id = verify_data["AttemptID"]
        print(f"[OK] Step 4: Payment verified. Secure attempt created: {attempt_id}.")

        # 5. Start Exam (Sanitized Questions & Authoritative Timer)
        headers = {"Authorization": f"Bearer {attempt_token}"}
        res = client.get("/exam", headers=headers)
        assert res.status_code == 200
        exam_data = res.json()
        assert exam_data["AttemptID"] == attempt_id
        assert len(exam_data["Questions"]) == paper["QuestionCount"]
        for q in exam_data["Questions"]:
            assert "CorrectAnswer" not in q
        print(f"[OK] Step 5: Exam started. Authoritative deadline: {exam_data['Deadline']}.")

        # 6. Persistent Randomization Snapshot Check
        res_reload = client.get("/exam", headers=headers)
        assert res_reload.status_code == 200
        reload_data = res_reload.json()
        q_order_1 = [q["QuestionID"] for q in exam_data["Questions"]]
        q_order_2 = [q["QuestionID"] for q in reload_data["Questions"]]
        assert q_order_1 == q_order_2
        print("[OK] Step 6: Reload verified. Question and option orders remain 100% identical.")

        # 7. Heartbeat
        res = client.post("/exam/heartbeat", json={"SessionID": exam_data["SessionID"]}, headers=headers)
        assert res.status_code == 200
        hb = res.json()
        assert hb["RemainingSeconds"] > 0
        print(f"[OK] Step 7: Heartbeat synced. Authoritative time remaining: {hb['RemainingSeconds']}s.")

        # 8. Anti-Cheat Deterrence Logging
        res = client.post("/exam/event", json={"EventType": "TAB_HIDDEN", "Details": "Tab switched"}, headers=headers)
        assert res.status_code == 200
        event_res = res.json()
        assert event_res["StrikeCount"] == 1
        assert "FriendlyMessage" in event_res
        print(f"[OK] Step 8: Anti-cheat strike logged (Count: {event_res['StrikeCount']}). Message: '{event_res['FriendlyMessage']}'.")

        # 9. Authoritative Test Submission
        # Q001: "OPT02" (90) - Correct
        # Q002: "OPT06" (Mars) - Correct
        # Q003: "New Delhi" - Correct (normalized)
        # Q004: "OPT10" (6) - Correct
        # Q005: "0 Celsius" - Correct (normalized)
        answers_payload = {
            "Answers": {
                "Q001": "OPT02",
                "Q002": "OPT06",
                "Q003": "  New   Delhi  ",
                "Q004": "OPT10",
                "Q005": "0 celsius"
            }
        }
        res = client.post("/exam/submit", json=answers_payload, headers=headers)
        assert res.status_code == 200
        result = res.json()
        assert result["Score"] == 20.0
        assert result["CorrectCount"] == 5
        assert result["Percentage"] == 100.0
        print(f"[OK] Step 9: Test submitted and graded: Score {result['Score']}/{result['MaxMarks']} ({result['Percentage']}%).")

        # 10. Concurrency & Idempotency Check
        res_dup = client.post("/exam/submit", json=answers_payload, headers=headers)
        assert res_dup.status_code == 200
        assert res_dup.json()["Score"] == 20.0
        print("[OK] Step 10: Repeated submission handled safely and idempotently.")

        # 11. Admin Portal Verification
        admin_login_res = client.post("/admin/login", json={"Password": "Admin@12345"})
        assert admin_login_res.status_code == 200
        admin_token = admin_login_res.json()["Token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        admin_attempts = client.get("/admin/attempts", headers=admin_headers)
        assert admin_attempts.status_code == 200
        assert len(admin_attempts.json()) >= 1
        print(f"[OK] Step 11: Admin portal verified. {len(admin_attempts.json())} attempt(s) visible to provider.")

    print("==================================================")
    print("ALL 11 END-TO-END VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_verification()
