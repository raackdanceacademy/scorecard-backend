import os
import secrets
from datetime import date
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from mangum import Mangum

# Import your custom modules (Must be in the same folder!)
from database import Base, engine, get_db
from models import Branch, ITSubmission, MonthlyScore
from schemas import ITSubmissionIn
from scoring import compute_full_score


# ============================================================
# APP INITIALIZATION
# ============================================================

app = FastAPI(
    title="RAACK Scorify — Smart Franchise Performance Scoring Platform",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)


# ============================================================
# STATIC FILES – ULTIMATE VERCELL FIX (Combined with main.py)
# ============================================================

# Vercel's Python runtime sets the current working directory to the repo root (which is your "backend" folder).
static_dir = os.path.join(os.getcwd(), "static")

# Fallback if the folder is nested one level up
if not os.path.exists(static_dir):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    static_dir = os.path.join(parent_dir, "static")

print(f"✅ Static directory resolved to: {static_dir}")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


# ============================================================
# MONTH PARSER & QUARTER HELPER (From main.py)
# ============================================================

def parse_month(month_str: str) -> date:
    try:
        year, month = month_str.strip().split("-")
        year = int(year)
        month = int(month)
        if month < 1 or month > 12:
            raise ValueError
        return date(year, month, 1)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

def get_quarter_start_month(month_date: date) -> date:
    year = month_date.year
    month = month_date.month
    if month in (6, 7, 8):
        return date(year, 6, 1)
    elif month in (9, 10, 11):
        return date(year, 9, 1)
    elif month in (12, 1, 2):
        if month == 12:
            return date(year, 12, 1)
        else:
            return date(year - 1, 12, 1)
    else:
        return date(year, 3, 1)


# ============================================================
# BRANCHES & CREDENTIALS (From main.py)
# ============================================================

BRANCHES = ["Kilpauk", "Mylapore", "Velachery", "Cuddalore", "Tambaram", "Mogappair", "Thoraipakkam", "Avadi", "Keelkattalai", "Mugalivakkam", "Sholinganallur", "Neelankarai", "Kolathur", "Pallikaranai", "Old Perungalathur", "Guduvanchery", "Puduchery", "Ramapuram", "Saidapet", "Old Pallavaram", "Mannivakkam", "Chidambaram", "Hasthinapuram", "Thiruverkadu", "Surapet", "Maraimalai Nagar", "Padur", "Medavakkam", "Ambattur", "Arumbakkam", "Ayapakkam", "Sithalapakkam", "Perumbakkam", "Basavanagudi", "Pudupakkam", "Urapakkam", "Thanjavur", "Pammal", "Kumbakonam", "Maduravoyal", "Kandigai", "Kundrathur", "Madambakkam", "Navalur", "Kelambakkam", "Iyyapanthangal", "Mappedu"]

BRANCH_ACCESS_CODES = { ... } # (Copy your full branch access codes here or keep the logic as is)

def _build_franchise_credentials():
    creds = {}
    for i, branch in enumerate(BRANCHES):
        mobile = f"9000001{str(i + 1).zfill(3)}"
        password = branch.lower().replace(" ", "") + "@123"
        creds[mobile] = {"branch": branch, "password": password}
    return creds

def initialize_branches():
    db = next(get_db())
    try:
        for branch_name in BRANCHES:
            existing = db.query(Branch).filter(Branch.name == branch_name).first()
            if not existing:
                access_code = BRANCH_ACCESS_CODES.get(branch_name, branch_name[:3].upper() + "123")
                db.add(Branch(name=branch_name, access_code=access_code))
        db.commit()
        print("✅ All branches initialized successfully!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error initializing branches: {e}")
        raise
    finally:
        db.close()

initialize_branches()


# ============================================================
# LOGIN & TOKEN VALIDATION (From main.py)
# ============================================================

ROLE_CREDENTIALS = {
    "it": {"mobile": "9000000001", "password": "it@123"},
    "accounts": {"mobile": "9000000002", "password": "accounts@345"},
    "superuser": {"mobile": "9000000003", "password": "super@1001"},
}

FRANCHISE_CREDENTIALS = _build_franchise_credentials()
ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}

class LoginIn(BaseModel):
    username: str
    password: str

@app.post("/api/login")
def login(payload: LoginIn):
    # ... (Paste your login logic here) ...
    # Return redirects like: "/dashboard?role=franchise&branch={branch}"
    pass

def get_current_user(authorization: str | None = Header(default=None)):
    # ... (Paste your token logic here) ...
    pass

@app.post("/api/logout")
def logout(user=Depends(get_current_user)):
    # ... 
    pass


# ============================================================
# PAGES (Combined with robust static_dir)
# ============================================================

@app.get("/")
async def serve_landing():
    return FileResponse(os.path.join(static_dir, "index.html")) if os.path.exists(os.path.join(static_dir, "index.html")) else {"error": "index.html not found"}

@app.get("/login")
async def serve_login():
    return FileResponse(os.path.join(static_dir, "login.html")) if os.path.exists(os.path.join(static_dir, "login.html")) else {"error": "login.html not found"}

@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse(os.path.join(static_dir, "dashboard.html")) if os.path.exists(os.path.join(static_dir, "dashboard.html")) else {"error": "dashboard.html not found"}

@app.get("/it-form")
async def serve_it_form():
    return FileResponse(os.path.join(static_dir, "it-form.html")) if os.path.exists(os.path.join(static_dir, "it-form.html")) else {"error": "it-form.html not found"}

@app.get("/formula")
async def serve_formula():
    return FileResponse(os.path.join(static_dir, "formula.html")) if os.path.exists(os.path.join(static_dir, "formula.html")) else {"error": "formula.html not found"}


# ============================================================
# IT SUBMISSION & DASHBOARD APIS (Paste the rest of main.py here)
# ============================================================
# ... (Keep all /api/it/submit, /api/it/get, /api/dashboard/all, etc. exactly as they are) ...


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "RAACK Scorify", "version": "1.0.0"}


# ============================================================
# VERCELL HANDLER – MUST BE AT THE VERY BOTTOM
# ============================================================

handler = Mangum(app)