import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.config import settings
from backend.models import init_db, SessionLocal, PaperModel
from backend.routers import papers, admin, payments, exams
from backend.utils.time import utc_now

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("exam_manager")

def seed_sample_paper():
    """Seeds a child-friendly sample paper if database is empty."""
    db = SessionLocal()
    try:
        existing = db.query(PaperModel).first()
        if not existing:
            sample_questions = [
                {
                    "QuestionID": "Q001",
                    "QuestionText": "What is 15 × 6?",
                    "ImageURL": "",
                    "ImageAltText": "",
                    "Type": "MCQ",
                    "Options": [
                        {"OptionID": "OPT01", "Text": "75"},
                        {"OptionID": "OPT02", "Text": "90"},
                        {"OptionID": "OPT03", "Text": "85"},
                        {"OptionID": "OPT04", "Text": "95"}
                    ],
                    "CorrectAnswer": "OPT02",
                    "MarksCorrect": 4.0,
                    "MarksNegative": 1.0
                },
                {
                    "QuestionID": "Q002",
                    "QuestionText": "Which planet is known as the Red Planet?",
                    "ImageURL": "",
                    "ImageAltText": "",
                    "Type": "MCQ",
                    "Options": [
                        {"OptionID": "OPT05", "Text": "Venus"},
                        {"OptionID": "OPT06", "Text": "Mars"},
                        {"OptionID": "OPT07", "Text": "Jupiter"},
                        {"OptionID": "OPT08", "Text": "Mercury"}
                    ],
                    "CorrectAnswer": "OPT06",
                    "MarksCorrect": 4.0,
                    "MarksNegative": 1.0
                },
                {
                    "QuestionID": "Q003",
                    "QuestionText": "What is the capital city of India?",
                    "ImageURL": "",
                    "ImageAltText": "",
                    "Type": "Text",
                    "Options": [],
                    "CorrectAnswer": "new delhi,delhi",
                    "MarksCorrect": 4.0,
                    "MarksNegative": 0.0
                },
                {
                    "QuestionID": "Q004",
                    "QuestionText": "How many sides does a hexagon have?",
                    "ImageURL": "",
                    "ImageAltText": "",
                    "Type": "MCQ",
                    "Options": [
                        {"OptionID": "OPT09", "Text": "5"},
                        {"OptionID": "OPT10", "Text": "6"},
                        {"OptionID": "OPT11", "Text": "7"},
                        {"OptionID": "OPT12", "Text": "8"}
                    ],
                    "CorrectAnswer": "OPT10",
                    "MarksCorrect": 4.0,
                    "MarksNegative": 1.0
                },
                {
                    "QuestionID": "Q005",
                    "QuestionText": "What is the freezing point of pure water in Celsius?",
                    "ImageURL": "",
                    "ImageAltText": "",
                    "Type": "Text",
                    "Options": [],
                    "CorrectAnswer": "0,0 c,0 celsius,zero",
                    "MarksCorrect": 4.0,
                    "MarksNegative": 0.0
                }
            ]

            now = utc_now()
            p = PaperModel(
                PaperID="pap_math_gk_01",
                Title="Class 5-7 Math & Science Starter Challenge",
                PriceMinorUnits=4900,  # ₹49.00
                Currency="INR",
                TimeLimitMinutes=20,
                Status="PUBLISHED",
                Version=1,
                NegativeMarkingEnabled=True,
                ShowAnswerKey=True,
                AllowResume=True,
                AntiCheatPolicy="AUTO_SUBMIT_ON_3",
                QuestionsJSON=json.dumps(sample_questions),
                CreatedAt=now,
                UpdatedAt=now
            )
            db.add(p)
            db.commit()
            logger.info("Seeded initial published sample assessment paper.")
    except Exception as e:
        logger.warning(f"Failed to seed sample paper: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    init_db()
    seed_sample_paper()
    yield
    logger.info("Application shutting down.")

app = FastAPI(
    title="Online Assessment Website API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS Configuration (Restricted Origins - Section 18)
allowed_origins = [settings.FRONTEND_URL.rstrip("/")]
if settings.ENVIRONMENT == "development":
    allowed_origins.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security Headers Middleware (Section 52)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Enforce request size limit
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_REQUEST_BODY_SIZE:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request payload too large."}
        )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# Clean Error Handlers (Never expose internal stack traces - Section 56)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = []
    for err in exc.errors():
        formatted_errors.append({
            "loc": err.get("loc"),
            "msg": str(err.get("msg")),
            "type": err.get("type")
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Please check your inputs and try again.", "errors": formatted_errors}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A temporary service error occurred. Please try again in a few moments."}
    )

# Include Routers
app.include_router(papers.router)
app.include_router(admin.router)
app.include_router(payments.router)
app.include_router(exams.router)

# Direct root-level routing for /paper and /submit
app.add_api_route("/paper/{paper_id}/{payment_id}", exams.get_paper_by_payment, methods=["GET"])
app.add_api_route("/submit/{paper_id}/{payment_id}", exams.submit_paper_by_payment, methods=["POST"])

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": utc_now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
