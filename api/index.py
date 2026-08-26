import os
import secrets
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from mangum import Mangum

app = FastAPI(title="RAACK Scorify", version="1.0.0")

# ============================================================
# STATIC FILES – Serve from /static and also from root
# ============================================================

current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")

# Mount the /static path
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")
    print(f"✅ Static directory mounted: {static_dir}")

# Helper to serve any file from static if requested at root
def serve_static_file(filename: str):
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return None

# ============================================================
# HTML PAGE ROUTES (must come before catch‑all)
# ============================================================

@app.get("/")
async def serve_index():
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
# CATCH‑ALL ROUTE TO SERVE STATIC FILES FROM ROOT (like /logo.png)
# ============================================================

@app.get("/{path:path}")
async def serve_any_static(path: str):
    # If the path starts with "api/" or is already handled by specific routes, skip
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    # Try to serve from static directory
    file_path = os.path.join(static_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    # Otherwise 404
    raise HTTPException(status_code=404, detail="File not found")

# ============================================================
# LOGIN API (hardcoded credentials – no database needed)
# ============================================================

class LoginIn(BaseModel):
    username: str
    password: str

# Role credentials (from your original main.py)
ROLE_CREDENTIALS = {
    "it": {"mobile": "9000000001", "password": "it@123"},
    "accounts": {"mobile": "9000000002", "password": "accounts@345"},
    "superuser": {"mobile": "9000000003", "password": "super@1001"},
}

# Franchise credentials (generated from your branch list)
BRANCHES = [
    "Kilpauk","Mylapore","Velachery","Cuddalore","Tambaram","Mogappair",
    "Thoraipakkam","Avadi","Keelkattalai","Mugalivakkam","Sholinganallur",
    "Neelankarai","Kolathur","Pallikaranai","Old Perungalathur","Guduvanchery",
    "Puduchery","Ramapuram","Saidapet","Old Pallavaram","Mannivakkam",
    "Chidambaram","Hasthinapuram","Thiruverkadu","Surapet","Maraimalai Nagar",
    "Padur","Medavakkam","Ambattur","Arumbakkam","Ayapakkam","Sithalapakkam",
    "Perumbakkam","Basavanagudi","Pudupakkam","Urapakkam","Thanjavur","Pammal",
    "Kumbakonam","Maduravoyal","Kandigai","Kundrathur","Madambakkam","Navalur",
    "Kelambakkam","Iyyapanthangal","Mappedu"
]

def _build_franchise_credentials():
    creds = {}
    for i, branch in enumerate(BRANCHES):
        mobile = f"9000001{str(i + 1).zfill(3)}"
        password = branch.lower().replace(" ", "") + "@123"
        creds[mobile] = {"branch": branch, "password": password}
    return creds

FRANCHISE_CREDENTIALS = _build_franchise_credentials()
ACTIVE_TOKENS = {}  # in‑memory token store

@app.post("/api/login")
async def login(payload: LoginIn):
    username = payload.username.strip()
    password = payload.password
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required.")

    # Check role login
    for role, cred in ROLE_CREDENTIALS.items():
        if username == cred["mobile"] and password == cred["password"]:
            token = secrets.token_hex(32)
            ACTIVE_TOKENS[token] = {"role": role, "username": username, "branch": None}
            return {
                "status": "ok",
                "access_token": token,
                "role": role,
                "username": username,
                "redirect": f"/dashboard?role={role}",
            }

    # Check franchise login
    franchise = FRANCHISE_CREDENTIALS.get(username)
    if franchise and password == franchise["password"]:
        token = secrets.token_hex(32)
        ACTIVE_TOKENS[token] = {"role": "franchise", "username": username, "branch": franchise["branch"]}
        return {
            "status": "ok",
            "access_token": token,
            "role": "franchise",
            "username": username,
            "branch": franchise["branch"],
            "redirect": f"/dashboard?role=franchise&branch={franchise['branch']}",
        }

    raise HTTPException(status_code=401, detail="Invalid username or password.")

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "RAACK Scorify", "version": "1.0.0"}

# ============================================================
# VERCELL HANDLER – MUST BE AT THE BOTTOM
# ============================================================

handler = Mangum(app)