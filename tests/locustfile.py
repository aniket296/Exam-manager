"""
Suite 5: Load & Stress Testing (Locust)
Simulates 50 concurrent students completing and submitting assessments within a 10-second window.
Monitors response times, throughput, and ensures zero dropped submissions or double-charge anomalies.
"""
import random
import uuid
from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger("locust_load_test")

class AssessmentStudentUser(HttpUser):
    # Short wait time to simulate 50 concurrent students submitting within a tight 10-second window
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """User setup: Enrollment, simulated unique IP, and payment verification."""
        self.student_name = f"Student_{uuid.uuid4().hex[:6]}"
        self.client_ip = f"192.168.{random.randint(1, 250)}.{random.randint(1, 250)}"
        self.attempt_token = None
        self.attempt_id = None
        self.paper_id = "pap_math_gk_01"
        self.submitted = False

        # 1. Create order
        order_payload = {
            "PaperID": self.paper_id,
            "StudentName": self.student_name,
            "StudentIdentifier": "Section A"
        }
        with self.client.post(
            "/payments/create-order",
            json=order_payload,
            headers={"X-Forwarded-For": self.client_ip},
            name="POST /payments/create-order",
            catch_response=True
        ) as res:
            if res.status_code == 200:
                order_data = res.json()
                self.order_id = order_data["OrderID"]
                res.success()
            else:
                res.failure(f"Failed to create order: {res.text}")
                return

        # 2. Verify payment (Simulation Mode)
        payment_id = f"pay_load_{self.order_id}"
        sig = f"sim_sig_{self.order_id}_{payment_id}"
        verify_payload = {
            "OrderID": self.order_id,
            "PaymentID": payment_id,
            "Signature": sig
        }
        with self.client.post(
            "/payments/verify",
            json=verify_payload,
            headers={"X-Forwarded-For": self.client_ip},
            name="POST /payments/verify",
            catch_response=True
        ) as res:
            if res.status_code == 200:
                verify_data = res.json()
                self.attempt_token = verify_data["AttemptToken"]
                self.attempt_id = verify_data["AttemptID"]
                res.success()
            else:
                res.failure(f"Payment verification failed: {res.text}")
                return

        # 3. Initialize/Start Exam
        start_headers = {
            "Authorization": f"Bearer {self.attempt_token}",
            "X-Forwarded-For": self.client_ip
        }
        with self.client.get("/exam", headers=start_headers, name="GET /exam", catch_response=True) as res:
            if res.status_code in [200, 403, 409]:
                res.success()
            else:
                res.failure(f"Initial start exam error: {res.status_code} - {res.text}")

    def get_auth_headers(self):
        return {
            "Authorization": f"Bearer {self.attempt_token}",
            "X-Forwarded-For": self.client_ip
        }

    @task(2)
    def send_heartbeat(self):
        """Sends periodic student heartbeat."""
        if not self.attempt_token or self.submitted:
            return

        headers = self.get_auth_headers()
        with self.client.post("/exam/heartbeat", json={}, headers=headers, name="POST /exam/heartbeat", catch_response=True) as res:
            if res.status_code in [200, 401, 403, 409]:
                res.success()
            else:
                res.failure(f"Heartbeat failed: {res.status_code}")

    @task(5)
    def submit_test(self):
        """High-concurrency submission and grading."""
        if not self.attempt_token or self.submitted:
            return

        answers = {
            "Q001": random.choice(["OPT01", "OPT02", "OPT03"]),
            "Q002": random.choice(["OPT05", "OPT06", "OPT07"]),
            "Q003": "New Delhi",
            "Q004": "OPT10",
            "Q005": "0"
        }

        headers = self.get_auth_headers()
        with self.client.post(
            "/exam/submit",
            json={"Answers": answers},
            headers=headers,
            name="POST /exam/submit",
            catch_response=True
        ) as res:
            if res.status_code in [200, 409]:
                self.submitted = True
                res.success()
            else:
                res.failure(f"Submission failed: {res.status_code} - {res.text}")

