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

# Import your custom modules (MUST be in the same folder as index.py)
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

# Wrap in try/except to avoid crashes if DB is temporarily unreachable during cold start
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"⚠️ Error creating tables (likely DB not connected): {e}")


# ============================================================
# STATIC FILES – ULTIMATE VERCELL FIX
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
# MONTH PARSER & QUARTER HELPER
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
# BRANCHES & CREDENTIALS
# ============================================================

BRANCHES = ["Kilpauk", "Mylapore", "Velachery", "Cuddalore", "Tambaram", "Mogappair", "Thoraipakkam", "Avadi", "Keelkattalai", "Mugalivakkam", "Sholinganallur", "Neelankarai", "Kolathur", "Pallikaranai", "Old Perungalathur", "Guduvanchery", "Puduchery", "Ramapuram", "Saidapet", "Old Pallavaram", "Mannivakkam", "Chidambaram", "Hasthinapuram", "Thiruverkadu", "Surapet", "Maraimalai Nagar", "Padur", "Medavakkam", "Ambattur", "Arumbakkam", "Ayapakkam", "Sithalapakkam", "Perumbakkam", "Basavanagudi", "Pudupakkam", "Urapakkam", "Thanjavur", "Pammal", "Kumbakonam", "Maduravoyal", "Kandigai", "Kundrathur", "Madambakkam", "Navalur", "Kelambakkam", "Iyyapanthangal", "Mappedu"]

BRANCH_ACCESS_CODES = {
    "Kilpauk": "KIL123", "Mylapore": "MYL456", "Velachery": "VEL789", "Cuddalore": "CUD101", "Tambaram": "TAM202", "Mogappair": "MOG303", "Thoraipakkam": "THO404", "Avadi": "AVA505", "Keelkattalai": "KEE606", "Mugalivakkam": "MUG707", "Sholinganallur": "SHO123", "Neelankarai": "NEE456", "Kolathur": "KOL789", "Pallikaranai": "PAL101", "Old Perungalathur": "OLD202", "Guduvanchery": "GUD303", "Puduchery": "PUD404", "Ramapuram": "RAM505", "Saidapet": "SAI606", "Old Pallavaram": "OLD707", "Mannivakkam": "MAN808", "Chidambaram": "CHI909", "Hasthinapuram": "HAS101", "Thiruverkadu": "THI202", "Surapet": "SUR303", "Maraimalai Nagar": "MAR404", "Padur": "PAD505", "Medavakkam": "MED606", "Ambattur": "AMB707", "Arumbakkam": "ARU808", "Ayapakkam": "AYA909", "Sithalapakkam": "SIT101", "Perumbakkam": "PER202", "Basavanagudi": "BAS303", "Pudupakkam": "PUD404", "Urapakkam": "URA505", "Thanjavur": "THA606", "Pammal": "PAM707", "Kumbakonam": "KUM808", "Maduravoyal": "MAD909", "Kandigai": "KAN101", "Kundrathur": "KUN202", "Madambakkam": "MAD303", "Navalur": "NAV404", "Kelambakkam": "KEL505", "Iyyapanthangal": "IYY606", "Mappedu": "MAP707"
}

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
    finally:
        db.close()

# Wrap execution to prevent crash if DB is down on startup
try:
    initialize_branches()
except Exception as e:
    print(f"⚠️ Could not initialize branches (DB may not be reachable): {e}")


# ============================================================
# LOGIN & TOKEN VALIDATION
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
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    # Role login
    for role, cred in ROLE_CREDENTIALS.items():
        if username == cred["mobile"] and password == cred["password"]:
            access_token = secrets.token_hex(32)
            ACTIVE_TOKENS[access_token] = {"role": role, "username": username, "branch": None}
            return {"status": "ok", "access_token": access_token, "role": role, "username": username, "redirect": f"/dashboard?role={role}"}

    # Franchise login
    franchise = FRANCHISE_CREDENTIALS.get(username)
    if franchise and password == franchise["password"]:
        access_token = secrets.token_hex(32)
        ACTIVE_TOKENS[access_token] = {"role": "franchise", "username": username, "branch": franchise["branch"]}
        return {"status": "ok", "access_token": access_token, "role": "franchise", "username": username, "branch": franchise["branch"], "redirect": f"/dashboard?role=franchise&branch={franchise['branch']}"}

    raise HTTPException(status_code=401, detail="Invalid username or password.")

def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token required.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format.")
    token = authorization.replace("Bearer ", "", 1).strip()
    user = ACTIVE_TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    return {"token": token, **user}

@app.post("/api/logout")
def logout(user=Depends(get_current_user)):
    ACTIVE_TOKENS.pop(user["token"], None)
    return {"status": "ok", "message": "Logged out successfully."}

@app.get("/api/me")
def current_user(user=Depends(get_current_user)):
    return {"status": "ok", "role": user["role"], "username": user["username"], "branch": user["branch"]}


# ============================================================
# PAGES
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
# REST OF MAIN.PY LOGIC (IT Form, Dashboard, Exports)
# ============================================================

def submission_to_dict(it_sub):
    if not it_sub:
        return {}
    return { ... } # (Paste the dictionary fields from your main.py here)

def _safe_pct(numerator, denominator, cap=None): ...
def _safe_num(value, default=0.0): ...
def compute_submetrics(it_sub) -> Dict[str, float]: ...

def _score_dict(score): ...

@app.post("/api/it/submit")
def submit_it_form(payload: ITSubmissionIn, db: Session = Depends(get_db)): ...

@app.get("/api/it/submission")
def get_it_submission(branch: str, month: str, db: Session = Depends(get_db)): ...

@app.get("/api/it/get")
def get_it_submission_flat(branch: str, report_month: str, db: Session = Depends(get_db)): ...

@app.get("/api/it/all")
def get_all_it_submissions_for_month(month: str, db: Session = Depends(get_db)): ...

@app.delete("/api/it/submission")
def delete_it_submission(branch: str, month: str, db: Session = Depends(get_db)): ...

def _recalculate_score(db: Session, branch_id: int, report_month: date): ...

@app.get("/api/dashboard/branch/{branch_name}")
def get_branch_score(branch_name: str, month: str, db: Session = Depends(get_db)): ...

@app.get("/api/dashboard/all")
def get_all_scores(month: str, db: Session = Depends(get_db)): ...

@app.get("/api/export/branch/{branch_name}")
def export_branch_month(branch_name: str, month: str, db: Session = Depends(get_db)): ...

@app.get("/api/export/all")
def export_all_branches(month: str, db: Session = Depends(get_db)): ...

@app.get("/api/export/branch/{branch_name}/history")
def export_branch_history(branch_name: str, db: Session = Depends(get_db)): ...

@app.get("/api/branches")
def get_branches(db: Session = Depends(get_db)): ...


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