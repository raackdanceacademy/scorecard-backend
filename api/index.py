import os
import secrets
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mangum import Mangum

# --- DATABASE IS DISABLED FOR NOW (Comment these out to fix the crash) ---
# from database import Base, engine, get_db
# from models import Branch, ITSubmission, MonthlyScore
# from schemas import ITSubmissionIn
# from scoring import compute_full_score

app = FastAPI(title="RAACK Scorify", version="1.0.0")

# ============================================================
# STATIC FILES – POINT TO YOUR LOCAL STATIC FOLDER
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
static_dir = os.path.join(parent_dir, "static")  # Use "public" if you renamed it

# Serve everything under /static/* (logos, icons, etc.) directly from the static folder
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def _serve_page(filename: str):
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": f"File {filename} not found"}

# ============================================================
# HTML PAGES
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
# LOGIN API (Hardcoded – Works without Database)
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
# VERCELL HANDLER
# ============================================================
handler = Mangum(app)