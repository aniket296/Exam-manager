import urllib.request
import json

API_BASE = "http://127.0.0.1:8000"
FRONTEND_ORIGIN = "http://localhost:3000"

def make_req(path, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    headers["Origin"] = FRONTEND_ORIGIN
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode("utf-8")
        resp_headers = dict(resp.headers)
        return json.loads(content) if "application/json" in resp_headers.get("content-type", "") else content, resp.getcode(), resp_headers

def run_live_test():
    print("==================================================")
    print("LIVE RUNTIME VERIFICATION (PORT 8000 & 3000)")
    print("==================================================")

    # 1. Health & Security Headers
    data, code, headers = make_req("/health")
    assert code == 200
    assert data["status"] == "ok"
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    print("[PASS] 1. Live server healthy & security headers verified.")

    # 2. Public Papers Catalog
    papers, code, _ = make_req("/papers")
    assert code == 200
    assert len(papers) >= 1
    paper = papers[0]
    paper_id = paper["PaperID"]
    print(f"[PASS] 2. Catalog loaded: '{paper['Title']}' | Fee: Rs {paper['PriceMinorUnits']/100}.")

    # 3. Create Order
    order_data = {
        "PaperID": paper_id,
        "StudentName": "Aditya Roy",
        "StudentIdentifier": "Class 7-C",
        "Contact": "9988776655"
    }
    order_res, code, _ = make_req("/payments/create-order", method="POST", data=order_data)
    assert code == 200
    order_id = order_res["OrderID"]
    print(f"[PASS] 3. Order created: {order_id} (Authoritative Amount: Rs {order_res['AmountMinorUnits']/100}).")

    # 4. Verify Payment (Simulation Mode)
    payment_id = f"pay_live_{order_id}"
    sig = f"sim_sig_{order_id}_{payment_id}"
    verify_res, code, _ = make_req("/payments/verify", method="POST", data={
        "OrderID": order_id,
        "PaymentID": payment_id,
        "Signature": sig
    })
    assert code == 200
    assert verify_res["Success"] is True
    attempt_token = verify_res["AttemptToken"]
    attempt_id = verify_res["AttemptID"]
    print(f"[PASS] 4. Payment verified. Issued attempt: {attempt_id}.")

    # 5. Start Exam
    exam_headers = {"Authorization": f"Bearer {attempt_token}"}
    exam_res, code, _ = make_req("/exam", headers=exam_headers)
    assert code == 200
    assert exam_res["AttemptID"] == attempt_id
    assert len(exam_res["Questions"]) == paper["QuestionCount"]
    for q in exam_res["Questions"]:
        assert "CorrectAnswer" not in q
    print(f"[PASS] 5. Exam started. Authoritative deadline: {exam_res['Deadline']}.")

    # 6. Anti-Cheat Event
    event_res, code, _ = make_req("/exam/event", method="POST", data={
        "EventType": "WINDOW_BLUR",
        "Details": "Window switched"
    }, headers=exam_headers)
    assert code == 200
    assert event_res["StrikeCount"] == 1
    print(f"[PASS] 6. Anti-cheat event handled: Strike #{event_res['StrikeCount']}.")

    # 7. Submit Exam
    submit_res, code, _ = make_req("/exam/submit", method="POST", data={
        "Answers": {
            "Q001": "OPT02",
            "Q002": "OPT06",
            "Q003": "new delhi",
            "Q004": "OPT10",
            "Q005": "0"
        }
    }, headers=exam_headers)
    assert code == 200
    assert submit_res["Score"] == 20.0
    assert submit_res["Percentage"] == 100.0
    print(f"[PASS] 7. Exam graded: {submit_res['Score']}/{submit_res['MaxMarks']} ({submit_res['Percentage']}%).")

    # 8. Admin Portal Verification
    admin_login, code, _ = make_req("/admin/login", method="POST", data={"Password": "Admin@12345"})
    assert code == 200
    admin_token = admin_login["Token"]
    attempts_res, code, _ = make_req("/admin/attempts", headers={"Authorization": f"Bearer {admin_token}"})
    assert code == 200
    assert any(a["AttemptID"] == attempt_id for a in attempts_res)
    print(f"[PASS] 8. Admin dashboard logged student attempt with score {submit_res['Score']}.")

    print("==================================================")
    print("ALL LIVE TESTS COMPLETED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_live_test()

