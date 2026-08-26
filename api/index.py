from fastapi import FastAPI
from mangum import Mangum

# --- Add back your custom imports (with dot notation) ---
from .database import Base, engine, get_db
from .models import Branch, ITSubmission, MonthlyScore
from .schemas import ITSubmissionIn
from .scoring import compute_full_score

app = FastAPI(
    title="RAACK Scorify — Smart Franchise Performance Scoring Platform",
    version="1.0.0"
)

# --- COMMENT OUT startup code that accesses the database ---
# Base.metadata.create_all(bind=engine)
# initialize_branches()

# --- Add back your routes (copy all @app.get, @app.post, etc. from your full main.py) ---
# For now, keep the minimal routes to confirm that imports work:

@app.get("/")
async def root():
    return {"message": "Imports are working!"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "imports": "successful"}

# --- CRITICAL: Handler must be at the bottom ---
handler = Mangum(app)