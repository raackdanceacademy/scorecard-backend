import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from mangum import Mangum

# --- Uncomment these when your database is ready ---
# from .database import Base, engine, get_db
# from .models import Branch, ITSubmission, MonthlyScore
# from .schemas import ITSubmissionIn
# from .scoring import compute_full_score

app = FastAPI(
    title="RAACK Scorify — Smart Franchise Performance Scoring Platform",
    version="1.0.0"
)

# ============================================================
# STATIC FILES – SERVE HTML PAGES (FIXED PATH FOR VERCELL)
# ============================================================

# Vercel sets the working directory to your backend folder
static_dir = os.path.join(os.getcwd(), "static")

# Fallback if it's nested one level up (because index.py is in api/)
if not os.path.exists(static_dir):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    static_dir = os.path.join(parent_dir, "static")

# Mount the static folder so that /static/… works
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")
    print(f"✅ Static directory mounted: {static_dir}")
else:
    print(f"⚠️ Static directory not found: {static_dir}")

# Helper to serve HTML pages
def _serve_page(filename: str):
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": f"File {filename} not found"}

# ============================================================
# HTML PAGE ROUTES
# ============================================================

@app.get("/")
async def serve_landing():
    return _serve_page("index.html")

@app.get("/login")
async def serve_login():
    return _serve_page("login.html")

@app.get("/dashboard")
async def serve_dashboard():
    return _serve_page("dashboard.html")

@app.get("/it-form")
async def serve_it_form():
    return _serve_page("it-form.html")

@app.get("/formula")
async def serve_formula():
    return _serve_page("formula.html")

# ============================================================
# HEALTH CHECK (to verify deployment)
# ============================================================

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "RAACK Scorify", "version": "1.0.0"}

# ============================================================
# CRITICAL: VERCELL HANDLER – MUST BE AT THE BOTTOM
# ============================================================

handler = Mangum(app)