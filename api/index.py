import os
import secrets
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from mangum import Mangum

app = FastAPI(title="RAACK Scorify", version="1.0.0")

# ============================================================
# BULLETPROOF STATIC FILE FINDER (Prints paths to Vercel Logs)
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# List of all possible locations to find your index.html
possible_paths = [
    os.path.join(os.getcwd(), "public"),
    os.path.join(parent_dir, "public"),
    os.path.join(os.getcwd(), "static"),
    os.path.join(parent_dir, "static"),
]

public_dir = None
for path in possible_paths:
    if os.path.exists(path):
        public_dir = path
        break

if not public_dir:
    public_dir = possible_paths[0]

# *** CRITICAL: These lines show up in your Vercel Logs ***
print(f"🔍 Current Working Dir: {os.getcwd()}")
print(f"🔍 Parent Dir: {parent_dir}")
print(f"📁 Checking Path: {public_dir}")
print(f"📁 Does it exist? {os.path.exists(public_dir)}")
if os.path.exists(public_dir):
    print(f"📁 Files inside: {os.listdir(public_dir)}")

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
# LOGIN API (Hardcoded)
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

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "RAACK Scorify", "version": "1.0.0"}

handler = Mangum(app)