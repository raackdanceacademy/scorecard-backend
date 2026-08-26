import os
import secrets
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from mangum import Mangum

# --- Uncomment these when your database is ready ---
# from database import Base, engine, get_db
# from models import Branch, ITSubmission, MonthlyScore
# from schemas import ITSubmissionIn
# from scoring import compute_full_score

app = FastAPI(title="RAACK Scorify", version="1.0.0")

# ============================================================
# STATIC FILES – POINT TO PUBLIC FOLDER (Vercel Native)
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # Step up to backend/
public_dir = os.path.join(parent_dir, "public")

if os.path.exists(public_dir):
    # Vercel serves 'public' automatically, so we don't need to mount it.
    print(f"✅ Public directory resolved to: {public_dir}")
else:
    print(f"⚠️ Public directory not found: {public_dir}")

def _serve_page(filename: str):
    file_path = os.path.join(public_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": f"File {filename} not found"}

# ============================================================
# HTML PAGE ROUTES
# ============================================================
@app.get("/")
async def serve_landing(): return _serve_page("index.html")
@app.get("/login")
async def serve_login(): return _serve_page("login.html")
@app.get("/dashboard")
async def serve_dashboard(): return _serve_page("dashboard.html")
@app.get("/it-form")
async def serve_it_form(): return _serve_page("it-form.html")
@app.get("/formula")
async def serve_formula(): return _serve_page("formula.html")

# ============================================================
# LOGIN API (Hardcoded – works WITHOUT a database)
# ============================================================
ROLE_CREDENTIALS = {
    "it": {"mobile": "9000000001", "password": "it@123"},
    "accounts": {"mobile": "9000000002", "password": "accounts@345"},
    "superuser": {"mobile": "9000000003", "password": "super@1001"},
}
BRANCHES = ["Kilpauk", "Mylapore", "Velachery", "Cuddalore", "Tambaram", "Mogappair"]
def _build_franchise_credentials():
    creds = {}
    for i, branch in enumerate(BRANCHES):
        mobile = f"9000001{str(i + 1).zfill(3)}"
        password = branch.lower().replace(" ", "") + "@123"
        creds[mobile] = {"branch": branch, "password": password}
    return creds
FRANCHISE_CREDENTIALS = _build_franchise_credentials()
ACTIVE_TOKENS = {}

class LoginIn(BaseModel):
    username: str
    password: str

@app.post("/api/login")
async def login(payload: LoginIn):
    username = payload.username.strip(); password = payload.password
    for role, cred in ROLE_CREDENTIALS.items():
        if username == cred["mobile"] and password == cred["password"]:
            token = secrets.token_hex(32)
            ACTIVE_TOKENS[token] = {"role": role, "username": username, "branch": None}
            return {"status": "ok", "access_token": token, "role": role, "username": username, "redirect": f"/dashboard?role={role}"}
    franchise = FRANCHISE_CREDENTIALS.get(username)
    if franchise and password == franchise["password"]:
        token = secrets.token_hex(32)
        ACTIVE_TOKENS[token] = {"role": "franchise", "username": username, "branch": franchise["branch"]}
        return {"status": "ok", "access_token": token, "role": "franchise", "username": username, "branch": franchise["branch"], "redirect": f"/dashboard?role=franchise&branch={franchise['branch']}"}
    raise HTTPException(status_code=401, detail="Invalid username or password.")

# ============================================================
# MOCK DASHBOARD APIs (So the UI loads while you test!)
# ============================================================
@app.get("/api/dashboard/all")
async def get_all_scores():
    # Temporary dummy data so the interface doesn't crash
    return [
        {"branch": "Kilpauk", "final_score": 780, "rating": "Excellent", "action": "", "financial_health": 200, "student_growth": 190, "operations_discipline": 120, "brand_quality": 60, "customer_experience": 65, "local_marketing": 150, "base_score": 785, "penalty": 5},
        {"branch": "Mylapore", "final_score": 650, "rating": "Good", "action": "", "financial_health": 170, "student_growth": 160, "operations_discipline": 100, "brand_quality": 50, "customer_experience": 55, "local_marketing": 125, "base_score": 660, "penalty": 10}
    ]

@app.get("/api/dashboard/branch/{branch_name}")
async def get_branch_score(branch_name: str, month: str):
    return {"branch": branch_name, "rating": "Excellent", "final_score": 750, "financial_health": 190, "student_growth": 180, "operations_discipline": 110, "brand_quality": 60, "customer_experience": 60, "local_marketing": 150, "base_score": 750, "penalty": 0, "action": ""}

@app.get("/api/it/get")
async def get_it_submission_flat():
    return {"branch": "Kilpauk", "report_month": "2026-08", "revenue_actual": 100000}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "RAACK Scorify", "version": "1.0.0"}

# ============================================================
# CRITICAL: VERCELL HANDLER – MUST BE AT THE BOTTOM
# ============================================================
handler = Mangum(app)