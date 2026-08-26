import os
import secrets
from datetime import date
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mangum import Mangum
from sqlalchemy.orm import Session

from database import Base, engine, get_db, SessionLocal
from models import Branch, ITSubmission, MonthlyScore
from schemas import ITSubmissionIn
from scoring import compute_full_score, get_quarter_start_month, safe_div

app = FastAPI(title="RAACK Scorify", version="1.0.0")

# ============================================================
# STATIC FILES
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
static_dir = os.path.join(parent_dir, "static")

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
BRANCHES = [
    "Kilpauk", "Mylapore", "Velachery", "Cuddalore", "Tambaram", "Mogappair",
    "Thoraipakkam", "Avadi", "Keelkattalai", "Mugalivakkam", "Sholinganallur",
    "Neelankarai", "Kolathur", "Pallikaranai", "Old Perungalathur", "Guduvanchery",
    "Puduchery", "Ramapuram", "Saidapet", "Old Pallavaram", "Mannivakkam",
    "Chidambaram", "Hasthinapuram", "Thiruverkadu", "Surapet", "Maraimalai Nagar",
    "Padur", "Medavakkam", "Ambattur", "Arumbakkam", "Ayapakkam", "Sithalapakkam",
    "Perumbakkam", "Basavanagudi", "Pudupakkam", "Urapakkam", "Thanjavur", "Pammal",
    "Kumbakonam", "Maduravoyal", "Kandigai", "Kundrathur", "Madambakkam", "Navalur",
    "Kelambakkam", "Iyyapanthangal", "Mappedu",
]
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
# STARTUP — create tables + seed branches (never crashes the app)
# ============================================================
@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            for i, name in enumerate(BRANCHES):
                if not db.query(Branch).filter(Branch.name == name).first():
                    db.add(Branch(name=name, access_code=f"F{i + 1:02d}"))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Database not reachable at startup (will retry per-request): {e}")

# ============================================================
# HELPERS
# ============================================================
def parse_month(month_str: str) -> date:
    try:
        year, month = month_str.split("-")
        return date(int(year), int(month), 1)
    except Exception:
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format.")

def get_branch_or_404(db: Session, name: str) -> Branch:
    branch = db.query(Branch).filter(Branch.name == name).first()
    if not branch:
        raise HTTPException(status_code=404, detail=f"Branch '{name}' not found.")
    return branch

def get_quarter_submission(db: Session, branch_id: int, month_date: date):
    quarter_start = get_quarter_start_month(month_date)
    if quarter_start == month_date:
        return None
    return db.query(ITSubmission).filter_by(branch_id=branch_id, report_month=quarter_start).first()

IT_SUBMISSION_FIELDS = [
    "revenue_target", "revenue_actual", "tshirt_due", "tshirt_paid", "salary_due", "salary_paid",
    "hotel_due", "hotel_paid", "merch_due", "merch_paid", "fee_collection_rate", "operating_margin",
    "opening_students", "new_student_target", "new_enrollments", "dropouts", "closing_students",
    "attendance_recording", "crm_usage", "report_submission",
    "branding_compliance", "mystery_audit_score",
    "satisfaction_score", "google_rating", "complaints_received", "complaints_resolved",
    "referrals", "event_satisfaction",
    "marketing_activities", "partnerships",
    "unauthorized_discount", "false_reporting", "trainer_misconduct", "comments",
]

def it_submission_to_dict(it_sub: ITSubmission, branch_name: str) -> dict:
    result = {"branch": branch_name, "report_month": it_sub.report_month.strftime("%Y-%m")}
    for field in IT_SUBMISSION_FIELDS:
        result[field] = getattr(it_sub, field, None)
    return result

def compute_submetric_percents(it_sub: ITSubmission) -> dict:
    total_due = (it_sub.tshirt_due or 0) + (it_sub.salary_due or 0) + (it_sub.hotel_due or 0) + (it_sub.merch_due or 0)
    total_paid = (it_sub.tshirt_paid or 0) + (it_sub.salary_paid or 0) + (it_sub.hotel_paid or 0) + (it_sub.merch_paid or 0)
    opening = it_sub.opening_students or 0
    new_students = it_sub.new_enrollments or 0
    dropouts = it_sub.dropouts or 0

    return {
        "revenue_achievement_pct": round(safe_div(it_sub.revenue_actual or 0, it_sub.revenue_target or 0, 0) * 100),
        "fee_collection_rate_pct": round((it_sub.fee_collection_rate or 0) * 100),
        "operating_margin_pct": round((it_sub.operating_margin or 0) * 100),
        "payment_discipline_pct": round(safe_div(total_paid, total_due, 1) * 100),
        "admission_achievement_pct": round(safe_div(new_students, it_sub.new_student_target or 0, 0) * 100),
        "retention_pct": round(safe_div(opening + new_students - dropouts, max(1, opening + new_students), 0) * 100),
        "attendance_recording_compliance_pct": round((it_sub.attendance_recording or 0) * 100),
        "crm_app_usage_pct": round((it_sub.crm_usage or 0) * 100),
        "report_submission_compliance_pct": round((it_sub.report_submission or 0) * 100),
        "branding_compliance_pct": round((it_sub.branding_compliance or 0) * 100),
        "mystery_audit_score_pct": round((it_sub.mystery_audit_score or 0) * 100),
        "satisfaction_score_pct": round((it_sub.satisfaction_score or 0) * 100),
        "google_rating_normalized": it_sub.google_rating or 0,
        "complaint_resolution_pct": round(safe_div(it_sub.complaints_resolved or 0, it_sub.complaints_received or 0, 1) * 100),
        "referrals_normalized": it_sub.referrals or 0,
        "event_satisfaction_pct": round((it_sub.event_satisfaction or 0) * 100),
        "marketing_activities_completed": it_sub.marketing_activities or 0,
        "partnerships_activated": it_sub.partnerships or 0,
    }

def build_dashboard_payload(branch_name: str, it_sub: ITSubmission, score_row: MonthlyScore) -> dict:
    if not score_row or not it_sub:
        return {"branch": branch_name, "rating": "No Data"}
    payload = {
        "branch": branch_name,
        "financial_health": score_row.financial_health,
        "student_growth": score_row.student_growth,
        "operations_discipline": score_row.operations_discipline,
        "brand_quality": score_row.brand_quality,
        "customer_experience": score_row.customer_experience,
        "local_marketing": score_row.local_marketing,
        "base_score": score_row.base_score,
        "penalty": score_row.penalty,
        "final_score": score_row.final_score,
        "rating": score_row.rating,
        "action": score_row.action,
    }
    payload.update(compute_submetric_percents(it_sub))
    return payload

# ============================================================
# IT SUBMISSION API
# ============================================================
@app.post("/api/it/submit")
async def submit_it_form(payload: ITSubmissionIn, db: Session = Depends(get_db)):
    branch = get_branch_or_404(db, payload.branch)
    month_date = parse_month(payload.report_month)

    data = payload.dict(exclude={"branch", "report_month"})
    it_sub = db.query(ITSubmission).filter_by(branch_id=branch.id, report_month=month_date).first()
    if it_sub:
        for k, v in data.items():
            setattr(it_sub, k, v)
    else:
        it_sub = ITSubmission(branch_id=branch.id, report_month=month_date, **data)
        db.add(it_sub)
    db.commit()
    db.refresh(it_sub)

    quarter_sub = get_quarter_submission(db, branch.id, month_date)
    result = compute_full_score(it_sub, quarter_sub=quarter_sub)

    score_row = db.query(MonthlyScore).filter_by(branch_id=branch.id, report_month=month_date).first()
    if not score_row:
        score_row = MonthlyScore(branch_id=branch.id, report_month=month_date)
        db.add(score_row)
    for k, v in result.items():
        setattr(score_row, k, v)
    db.commit()

    return {"status": "ok", "message": "Submission saved.", "score": result}

@app.get("/api/it/get")
async def get_it_submission(branch: str, report_month: str, db: Session = Depends(get_db)):
    b = get_branch_or_404(db, branch)
    month_date = parse_month(report_month)
    it_sub = db.query(ITSubmission).filter_by(branch_id=b.id, report_month=month_date).first()
    if not it_sub:
        raise HTTPException(status_code=404, detail="No submission found for this branch/month.")
    return it_submission_to_dict(it_sub, branch)

# ============================================================
# DASHBOARD API
# ============================================================
@app.get("/api/dashboard/branch/{branch}")
async def dashboard_branch(branch: str, month: str, db: Session = Depends(get_db)):
    b = get_branch_or_404(db, branch)
    month_date = parse_month(month)
    it_sub = db.query(ITSubmission).filter_by(branch_id=b.id, report_month=month_date).first()
    score_row = db.query(MonthlyScore).filter_by(branch_id=b.id, report_month=month_date).first()
    return build_dashboard_payload(branch, it_sub, score_row)

@app.get("/api/dashboard/all")
async def dashboard_all(month: str, db: Session = Depends(get_db)):
    month_date = parse_month(month)
    branches = db.query(Branch).order_by(Branch.name).all()
    results = []
    for b in branches:
        it_sub = db.query(ITSubmission).filter_by(branch_id=b.id, report_month=month_date).first()
        score_row = db.query(MonthlyScore).filter_by(branch_id=b.id, report_month=month_date).first()
        results.append(build_dashboard_payload(b.name, it_sub, score_row))
    return results

@app.get("/api/branches")
async def list_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.name).all()
    return [b.name for b in branches] or BRANCHES

# ============================================================
# EXPORT API
# ============================================================
@app.get("/api/export/all")
async def export_all(month: str, db: Session = Depends(get_db)):
    month_date = parse_month(month)
    branches = db.query(Branch).order_by(Branch.name).all()
    rows = []
    for b in branches:
        score_row = db.query(MonthlyScore).filter_by(branch_id=b.id, report_month=month_date).first()
        row = {"Branch": b.name, "Month": month}
        if score_row:
            row.update({
                "Final Score": score_row.final_score,
                "Rating": score_row.rating,
                "Base Score": score_row.base_score,
                "Penalty": score_row.penalty,
                "Financial Health": score_row.financial_health,
                "Student Growth": score_row.student_growth,
                "Operations Discipline": score_row.operations_discipline,
                "Brand & Quality": score_row.brand_quality,
                "Customer Experience": score_row.customer_experience,
                "Local Marketing": score_row.local_marketing,
                "Action": score_row.action,
            })
        else:
            row["Rating"] = "No Data"
        rows.append(row)
    return rows

@app.get("/api/export/branch/{branch}/history")
async def export_branch_history(branch: str, db: Session = Depends(get_db)):
    b = get_branch_or_404(db, branch)
    scores = db.query(MonthlyScore).filter_by(branch_id=b.id).order_by(MonthlyScore.report_month).all()
    rows = []
    for s in scores:
        rows.append({
            "Month": s.report_month.strftime("%Y-%m"),
            "Final Score": s.final_score,
            "Rating": s.rating,
            "Base Score": s.base_score,
            "Penalty": s.penalty,
            "Financial Health": s.financial_health,
            "Student Growth": s.student_growth,
            "Operations Discipline": s.operations_discipline,
            "Brand & Quality": s.brand_quality,
            "Customer Experience": s.customer_experience,
            "Local Marketing": s.local_marketing,
            "Action": s.action,
        })
    return rows

# ============================================================
# VERCEL HANDLER
# ============================================================
handler = Mangum(app)