import secrets
from datetime import date
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Branch, ITSubmission, MonthlyScore
from schemas import ITSubmissionIn
from scoring import compute_full_score


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="RAACK Scorify — Smart Franchise Performance Scoring Platform",
    version="1.0.0"
)


# ============================================================
# CREATE TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# MONTH PARSER
# ============================================================

def parse_month(month_str: str) -> date:
    """
    Convert YYYY-MM into a date object.
    Example:
        2026-08 -> date(2026, 8, 1)
    """
    try:
        year, month = month_str.strip().split("-")
        year = int(year)
        month = int(month)

        if month < 1 or month > 12:
            raise ValueError

        return date(year, month, 1)

    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM."
        )


# ============================================================
# QUARTER START HELPER (Academic year: June – May)
# ============================================================

def get_quarter_start_month(month_date: date) -> date:
    """
    Return the first month of the academic quarter for the given month.
    Quarters: Jun-Jul-Aug, Sep-Oct-Nov, Dec-Jan-Feb, Mar-Apr-May.
    """
    year = month_date.year
    month = month_date.month

    if month in (6, 7, 8):
        return date(year, 6, 1)
    elif month in (9, 10, 11):
        return date(year, 9, 1)
    elif month in (12, 1, 2):
        if month == 12:
            return date(year, 12, 1)
        else:  # Jan, Feb belong to previous year's quarter
            return date(year - 1, 12, 1)
    else:  # 3, 4, 5
        return date(year, 3, 1)


# ============================================================
# BRANCHES
# ============================================================

BRANCHES = [
    "Kilpauk",
    "Mylapore",
    "Velachery",
    "Cuddalore",
    "Tambaram",
    "Mogappair",
    "Thoraipakkam",
    "Avadi",
    "Keelkattalai",
    "Mugalivakkam",
    "Sholinganallur",
    "Neelankarai",
    "Kolathur",
    "Pallikaranai",
    "Old Perungalathur",
    "Guduvanchery",
    "Puduchery",
    "Ramapuram",
    "Saidapet",
    "Old Pallavaram",
    "Mannivakkam",
    "Chidambaram",
    "Hasthinapuram",
    "Thiruverkadu",
    "Surapet",
    "Maraimalai Nagar",
    "Padur",
    "Medavakkam",
    "Ambattur",
    "Arumbakkam",
    "Ayapakkam",
    "Sithalapakkam",
    "Perumbakkam",
    "Basavanagudi",
    "Pudupakkam",
    "Urapakkam",
    "Thanjavur",
    "Pammal",
    "Kumbakonam",
    "Maduravoyal",
    "Kandigai",
    "Kundrathur",
    "Madambakkam",
    "Navalur",
    "Kelambakkam",
    "Iyyapanthangal",
    "Mappedu",
]


# ============================================================
# BRANCH ACCESS CODES
# ============================================================

BRANCH_ACCESS_CODES = {
    "Kilpauk": "KIL123",
    "Mylapore": "MYL456",
    "Velachery": "VEL789",
    "Cuddalore": "CUD101",
    "Tambaram": "TAM202",
    "Mogappair": "MOG303",
    "Thoraipakkam": "THO404",
    "Avadi": "AVA505",
    "Keelkattalai": "KEE606",
    "Mugalivakkam": "MUG707",
    "Sholinganallur": "SHO123",
    "Neelankarai": "NEE456",
    "Kolathur": "KOL789",
    "Pallikaranai": "PAL101",
    "Old Perungalathur": "OLD202",
    "Guduvanchery": "GUD303",
    "Puduchery": "PUD404",
    "Ramapuram": "RAM505",
    "Saidapet": "SAI606",
    "Old Pallavaram": "OLD707",
    "Mannivakkam": "MAN808",
    "Chidambaram": "CHI909",
    "Hasthinapuram": "HAS101",
    "Thiruverkadu": "THI202",
    "Surapet": "SUR303",
    "Maraimalai Nagar": "MAR404",
    "Padur": "PAD505",
    "Medavakkam": "MED606",
    "Ambattur": "AMB707",
    "Arumbakkam": "ARU808",
    "Ayapakkam": "AYA909",
    "Sithalapakkam": "SIT101",
    "Perumbakkam": "PER202",
    "Basavanagudi": "BAS303",
    "Pudupakkam": "PUD404",
    "Urapakkam": "URA505",
    "Thanjavur": "THA606",
    "Pammal": "PAM707",
    "Kumbakonam": "KUM808",
    "Maduravoyal": "MAD909",
    "Kandigai": "KAN101",
    "Kundrathur": "KUN202",
    "Madambakkam": "MAD303",
    "Navalur": "NAV404",
    "Kelambakkam": "KEL505",
    "Iyyapanthangal": "IYY606",
    "Mappedu": "MAP707",
}


# ============================================================
# INITIALIZE BRANCHES IN DATABASE
# ============================================================

def initialize_branches():
    """
    Make sure every branch in BRANCHES exists in the database.
    Existing branches are not duplicated.
    """
    db = next(get_db())

    try:
        for branch_name in BRANCHES:
            existing = (
                db.query(Branch)
                .filter(Branch.name == branch_name)
                .first()
            )

            if not existing:
                # Get access code from dictionary, or generate one
                access_code = BRANCH_ACCESS_CODES.get(
                    branch_name,
                    branch_name[:3].upper() + "123"
                )
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
# LOGIN
# ============================================================

ROLE_CREDENTIALS = {
    "it": {
        "mobile": "9000000001",
        "password": "it@123",
    },
    "accounts": {
        "mobile": "9000000002",
        "password": "accounts@345",
    },
    "superuser": {
        "mobile": "9000000003",
        "password": "super@1001",
    },
}


# ============================================================
# FRANCHISE LOGIN CREDENTIALS
# ============================================================

def _build_franchise_credentials():
    creds = {}

    for i, branch in enumerate(BRANCHES):
        mobile = f"9000001{str(i + 1).zfill(3)}"
        password = (
            branch
            .lower()
            .replace(" ", "")
            + "@123"
        )

        creds[mobile] = {
            "branch": branch,
            "password": password,
        }

    return creds


FRANCHISE_CREDENTIALS = _build_franchise_credentials()


# ============================================================
# ACTIVE TOKENS
# ============================================================

ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}


# ============================================================
# LOGIN MODEL
# ============================================================

class LoginIn(BaseModel):
    username: str
    password: str


# ============================================================
# LOGIN API
# ============================================================

@app.post("/api/login")
def login(payload: LoginIn):
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="Username and password are required."
        )

    # --------------------------------------------------------
    # ROLE LOGIN
    # --------------------------------------------------------

    for role, cred in ROLE_CREDENTIALS.items():
        if (
            username == cred["mobile"]
            and password == cred["password"]
        ):
            access_token = secrets.token_hex(32)

            ACTIVE_TOKENS[access_token] = {
                "role": role,
                "username": username,
                "branch": None,
            }

            return {
                "status": "ok",
                "access_token": access_token,
                "role": role,
                "username": username,
                "redirect": f"/dashboard?role={role}",
            }

    # --------------------------------------------------------
    # FRANCHISE LOGIN
    # --------------------------------------------------------

    franchise = FRANCHISE_CREDENTIALS.get(username)

    if franchise and password == franchise["password"]:
        access_token = secrets.token_hex(32)

        ACTIVE_TOKENS[access_token] = {
            "role": "franchise",
            "username": username,
            "branch": franchise["branch"],
        }

        return {
            "status": "ok",
            "access_token": access_token,
            "role": "franchise",
            "username": username,
            "branch": franchise["branch"],
            "redirect": (
                f"/dashboard"
                f"?role=franchise"
                f"&branch={franchise['branch']}"
            ),
        }

    raise HTTPException(
        status_code=401,
        detail="Invalid username or password."
    )


# ============================================================
# TOKEN VALIDATION
# ============================================================

def get_current_user(
    authorization: str | None = Header(default=None)
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization token required."
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format."
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    user = ACTIVE_TOKENS.get(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token."
        )

    return {
        "token": token,
        **user,
    }


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/logout")
def logout(
    user=Depends(get_current_user)
):
    token = user["token"]
    ACTIVE_TOKENS.pop(token, None)

    return {
        "status": "ok",
        "message": "Logged out successfully.",
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
def current_user(
    user=Depends(get_current_user)
):
    return {
        "status": "ok",
        "role": user["role"],
        "username": user["username"],
        "branch": user["branch"],
    }


# ============================================================
# PAGES
# ============================================================

@app.get("/")
def serve_landing():
    return FileResponse(
        "static/index.html"
    )


@app.get("/login")
def serve_login():
    return FileResponse(
        "static/login.html"
    )


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(
        "static/dashboard.html"
    )


@app.get("/it-form")
def serve_it_form():
    return FileResponse(
        "static/it-form.html"
    )


@app.get("/formula")
def serve_formula():
    return FileResponse(
        "static/formula.html"
    )


# ============================================================
# CONVERT IT SUBMISSION INTO DICTIONARY
# ============================================================

def submission_to_dict(it_sub):
    if not it_sub:
        return {}

    return {
        "branch": (
            it_sub.branch.name
            if it_sub.branch
            else ""
        ),

        "report_month": (
            it_sub.report_month.strftime("%Y-%m")
        ),

        "revenue_target": it_sub.revenue_target or 0,
        "revenue_actual": it_sub.revenue_actual or 0,

        "tshirt_due": it_sub.tshirt_due or 0,
        "tshirt_paid": it_sub.tshirt_paid or 0,

        "salary_due": it_sub.salary_due or 0,
        "salary_paid": it_sub.salary_paid or 0,

        "hotel_due": it_sub.hotel_due or 0,
        "hotel_paid": it_sub.hotel_paid or 0,

        "merch_due": it_sub.merch_due or 0,
        "merch_paid": it_sub.merch_paid or 0,

        "fee_collection_rate": (
            it_sub.fee_collection_rate or 0
        ),

        "operating_margin": (
            it_sub.operating_margin or 0
        ),

        "opening_students": (
            it_sub.opening_students or 0
        ),

        "new_student_target": (
            it_sub.new_student_target or 0
        ),

        "new_enrollments": (
            it_sub.new_enrollments or 0
        ),

        "dropouts": it_sub.dropouts or 0,

        "closing_students": (
            it_sub.closing_students or 0
        ),

        "attendance_recording": (
            it_sub.attendance_recording or 0
        ),

        "crm_usage": (
            it_sub.crm_usage or 0
        ),

        "report_submission": (
            it_sub.report_submission or 0
        ),

        # Quarterly fields (may be overridden by quarter-start values in endpoints)
        "branding_compliance": (
            it_sub.branding_compliance or 0
        ),

        "mystery_audit_score": (
            it_sub.mystery_audit_score or 0
        ),

        "satisfaction_score": (
            it_sub.satisfaction_score or 0
        ),

        "google_rating": (
            it_sub.google_rating or 0
        ),

        "complaints_received": (
            it_sub.complaints_received or 0
        ),

        "complaints_resolved": (
            it_sub.complaints_resolved or 0
        ),

        "referrals": (
            it_sub.referrals or 0
        ),

        "event_satisfaction": (
            it_sub.event_satisfaction or 0
        ),

        "marketing_activities": (
            it_sub.marketing_activities or 0
        ),

        "partnerships": (
            it_sub.partnerships or 0
        ),

        "unauthorized_discount": (
            it_sub.unauthorized_discount or "No"
        ),

        "false_reporting": (
            it_sub.false_reporting or "No"
        ),

        "trainer_misconduct": (
            it_sub.trainer_misconduct or "No"
        ),

        "comments": (
            it_sub.comments or ""
        ),
    }


# ============================================================
# SUB-METRIC PERCENTAGE COMPUTATION
# ============================================================

def _safe_pct(numerator, denominator, cap=None):
    try:
        numerator = float(numerator or 0)
        denominator = float(denominator or 0)
    except (TypeError, ValueError):
        return 0.0

    if denominator == 0:
        return 0.0

    pct = (numerator / denominator) * 100

    if cap is not None:
        pct = min(pct, cap)

    return round(pct, 1)


def _safe_num(value, default=0.0):
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return default


def compute_submetrics(it_sub) -> Dict[str, float]:
    if not it_sub:
        return {
            "revenue_achievement_pct": 0,
            "fee_collection_rate_pct": 0,
            "operating_margin_pct": 0,
            "payment_discipline_pct": 0,
            "admission_achievement_pct": 0,
            "retention_pct": 0,
            "attendance_recording_compliance_pct": 0,
            "crm_app_usage_pct": 0,
            "report_submission_compliance_pct": 0,
            "branding_compliance_pct": 0,
            "mystery_audit_score_pct": 0,
            "satisfaction_score_pct": 0,
            "google_rating_normalized": 0,
            "complaint_resolution_pct": 0,
            "referrals_normalized": 0,
            "event_satisfaction_pct": 0,
            "marketing_activities_completed": 0,
            "partnerships_activated": 0,
        }

    # Financial Health
    revenue_achievement_pct = _safe_pct(
        it_sub.revenue_actual, it_sub.revenue_target, cap=150
    )
    fee_collection_rate_pct = _safe_num(it_sub.fee_collection_rate)
    operating_margin_pct = _safe_num(it_sub.operating_margin)

    payment_components = []
    for due_field, paid_field in [
        (it_sub.tshirt_due, it_sub.tshirt_paid),
        (it_sub.salary_due, it_sub.salary_paid),
        (it_sub.hotel_due, it_sub.hotel_paid),
        (it_sub.merch_due, it_sub.merch_paid),
    ]:
        due = float(due_field or 0)
        paid = float(paid_field or 0)
        if due > 0:
            payment_components.append(min((paid / due) * 100, 100))

    payment_discipline_pct = (
        round(sum(payment_components) / len(payment_components), 1)
        if payment_components
        else 0
    )

    # Student Growth (removed batch_utilization, trial_conversion)
    admission_achievement_pct = _safe_pct(
        it_sub.new_enrollments, it_sub.new_student_target, cap=150
    )
    base_students = float(it_sub.opening_students or 0) + float(
        it_sub.new_enrollments or 0
    )
    retention_pct = (
        round(max(0.0, (1 - (float(it_sub.dropouts or 0) / base_students))) * 100, 1)
        if base_students > 0
        else 0
    )

    # Operations Discipline (removed class_delivery, trainer_attendance)
    attendance_recording_compliance_pct = _safe_num(
        it_sub.attendance_recording
    )
    crm_app_usage_pct = _safe_num(it_sub.crm_usage)
    report_submission_compliance_pct = _safe_num(
        it_sub.report_submission
    )

    # Brand & Quality (removed hygiene, curriculum, trainer_certification)
    branding_compliance_pct = _safe_num(it_sub.branding_compliance)
    mystery_audit_score_pct = _safe_num(it_sub.mystery_audit_score)

    # Customer Experience
    satisfaction_score_pct = _safe_num(it_sub.satisfaction_score)
    google_rating_normalized = _safe_num(it_sub.google_rating)
    complaint_resolution_pct = _safe_pct(
        it_sub.complaints_resolved, it_sub.complaints_received, cap=100
    ) if (it_sub.complaints_received or 0) > 0 else 100.0
    referrals_normalized = _safe_num(it_sub.referrals)
    event_satisfaction_pct = _safe_num(it_sub.event_satisfaction)

    # Local Marketing (removed social_media_posts, events_workshops)
    marketing_activities_completed = _safe_num(it_sub.marketing_activities)
    partnerships_activated = _safe_num(it_sub.partnerships)

    return {
        "revenue_achievement_pct": revenue_achievement_pct,
        "fee_collection_rate_pct": fee_collection_rate_pct,
        "operating_margin_pct": operating_margin_pct,
        "payment_discipline_pct": payment_discipline_pct,
        "admission_achievement_pct": admission_achievement_pct,
        "retention_pct": retention_pct,
        "attendance_recording_compliance_pct": attendance_recording_compliance_pct,
        "crm_app_usage_pct": crm_app_usage_pct,
        "report_submission_compliance_pct": report_submission_compliance_pct,
        "branding_compliance_pct": branding_compliance_pct,
        "mystery_audit_score_pct": mystery_audit_score_pct,
        "satisfaction_score_pct": satisfaction_score_pct,
        "google_rating_normalized": google_rating_normalized,
        "complaint_resolution_pct": complaint_resolution_pct,
        "referrals_normalized": referrals_normalized,
        "event_satisfaction_pct": event_satisfaction_pct,
        "marketing_activities_completed": marketing_activities_completed,
        "partnerships_activated": partnerships_activated,
    }


# ============================================================
# SCORE DICTIONARY
# ============================================================

def _score_dict(score):
    if not score:
        return {
            "financial_health": 0,
            "student_growth": 0,
            "operations_discipline": 0,
            "brand_quality": 0,
            "customer_experience": 0,
            "local_marketing": 0,
            "base_score": 0,
            "penalty": 0,
            "final_score": 0,
            "rating": "No Data",
            "action": "No data submitted",
        }

    return {
        "financial_health": int(round(score.financial_health or 0)),
        "student_growth": int(round(score.student_growth or 0)),
        "operations_discipline": int(round(score.operations_discipline or 0)),
        "brand_quality": int(round(score.brand_quality or 0)),
        "customer_experience": int(round(score.customer_experience or 0)),
        "local_marketing": int(round(score.local_marketing or 0)),
        "base_score": int(round(score.base_score or 0)),
        "penalty": int(round(score.penalty or 0)),
        "final_score": int(round(score.final_score or 0)),
        "rating": score.rating or "Critical",
        "action": score.action or "",
    }


# ============================================================
# CREATE / UPDATE IT FORM
# ============================================================

@app.post("/api/it/submit")
def submit_it_form(
    payload: ITSubmissionIn,
    db: Session = Depends(get_db),
):
    branch = (
        db.query(Branch)
        .filter(Branch.name == payload.branch)
        .first()
    )

    if not branch:
        raise HTTPException(
            status_code=404,
            detail=f"Branch not found: {payload.branch}",
        )

    report_month = parse_month(
        payload.report_month
    )

    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch.id,
            ITSubmission.report_month == report_month,
        )
        .first()
    )

    is_new = False

    if not it_sub:
        is_new = True
        it_sub = ITSubmission(
            branch_id=branch.id,
            report_month=report_month,
        )
        db.add(it_sub)

    # ---------- Operations (only remaining fields) ----------
    it_sub.attendance_recording = payload.attendance_recording
    it_sub.crm_usage = payload.crm_usage
    it_sub.report_submission = payload.report_submission

    # ---------- Brand & Quality (only remaining fields) ----------
    # Quarterly fields: only saved if month is a quarter start
    quarter_start = get_quarter_start_month(report_month)
    if report_month == quarter_start:
        it_sub.branding_compliance = payload.branding_compliance
        it_sub.mystery_audit_score = payload.mystery_audit_score
        it_sub.satisfaction_score = payload.satisfaction_score
    else:
        # For non-quarter months, do NOT save these fields (set to None)
        it_sub.branding_compliance = None
        it_sub.mystery_audit_score = None
        it_sub.satisfaction_score = None

    # Customer (unchanged)
    it_sub.google_rating = payload.google_rating
    it_sub.complaints_received = payload.complaints_received
    it_sub.complaints_resolved = payload.complaints_resolved
    it_sub.referrals = payload.referrals
    it_sub.event_satisfaction = payload.event_satisfaction

    # Financial (unchanged)
    it_sub.revenue_target = payload.revenue_target
    it_sub.revenue_actual = payload.revenue_actual
    it_sub.tshirt_due = payload.tshirt_due
    it_sub.tshirt_paid = payload.tshirt_paid
    it_sub.salary_due = payload.salary_due
    it_sub.salary_paid = payload.salary_paid
    it_sub.hotel_due = payload.hotel_due
    it_sub.hotel_paid = payload.hotel_paid
    it_sub.merch_due = payload.merch_due
    it_sub.merch_paid = payload.merch_paid
    it_sub.fee_collection_rate = payload.fee_collection_rate
    it_sub.operating_margin = payload.operating_margin

    # Students (removed batch_utilization, trials_conducted, trial_conversions)
    it_sub.opening_students = payload.opening_students
    it_sub.new_student_target = payload.new_student_target
    it_sub.new_enrollments = payload.new_enrollments
    it_sub.dropouts = payload.dropouts
    it_sub.closing_students = payload.closing_students  # kept (not used in scoring)

    # Marketing (removed social_media_posts, events_workshops)
    it_sub.marketing_activities = payload.marketing_activities
    it_sub.partnerships = payload.partnerships

    # Compliance / Penalties (unchanged)
    it_sub.unauthorized_discount = payload.unauthorized_discount
    it_sub.false_reporting = payload.false_reporting
    it_sub.trainer_misconduct = payload.trainer_misconduct
    it_sub.comments = payload.comments

    try:
        db.commit()
        db.refresh(it_sub)

        _recalculate_score(
            db,
            branch.id,
            report_month,
        )

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unable to save IT submission: {str(exc)}",
        )

    return {
        "status": "ok",
        "message": (
            "IT form created successfully"
            if is_new
            else "IT form updated successfully"
        ),
        "mode": (
            "created"
            if is_new
            else "updated"
        ),
        "branch": branch.name,
        "report_month": payload.report_month,
    }


# ============================================================
# GET EXISTING IT DATA
# ============================================================

@app.get("/api/it/submission")
def get_it_submission(
    branch: str,
    month: str,
    db: Session = Depends(get_db),
):
    branch_obj = (
        db.query(Branch)
        .filter(Branch.name == branch)
        .first()
    )

    if not branch_obj:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    report_month = parse_month(month)

    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch_obj.id,
            ITSubmission.report_month == report_month,
        )
        .first()
    )

    if not it_sub:
        return {
            "exists": False,
            "message": "No saved data found.",
        }

    data = submission_to_dict(it_sub)

    # If current month is not a quarter start, override quarterly fields with
    # values from the quarter-start submission (if it exists).
    quarter_start = get_quarter_start_month(report_month)
    if report_month != quarter_start:
        quarter_sub = (
            db.query(ITSubmission)
            .filter(
                ITSubmission.branch_id == branch_obj.id,
                ITSubmission.report_month == quarter_start,
            )
            .first()
        )
        if quarter_sub:
            data["branding_compliance"] = quarter_sub.branding_compliance or 0
            data["mystery_audit_score"] = quarter_sub.mystery_audit_score or 0
            data["satisfaction_score"] = quarter_sub.satisfaction_score or 0

    return {
        "exists": True,
        "data": data,
    }


# ============================================================
# GET EXISTING IT DATA — FLAT SHAPE
# ============================================================

@app.get("/api/it/get")
def get_it_submission_flat(
    branch: str,
    report_month: str,
    db: Session = Depends(get_db),
):
    branch_obj = (
        db.query(Branch)
        .filter(Branch.name == branch)
        .first()
    )

    if not branch_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Branch not found: {branch}",
        )

    parsed_month = parse_month(report_month)

    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch_obj.id,
            ITSubmission.report_month == parsed_month,
        )
        .first()
    )

    if not it_sub:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No saved data found for {branch} "
                f"— {report_month}."
            ),
        )

    data = submission_to_dict(it_sub)

    # If current month is not a quarter start, override quarterly fields with
    # values from the quarter-start submission (if it exists).
    quarter_start = get_quarter_start_month(parsed_month)
    if parsed_month != quarter_start:
        quarter_sub = (
            db.query(ITSubmission)
            .filter(
                ITSubmission.branch_id == branch_obj.id,
                ITSubmission.report_month == quarter_start,
            )
            .first()
        )
        if quarter_sub:
            data["branding_compliance"] = quarter_sub.branding_compliance or 0
            data["mystery_audit_score"] = quarter_sub.mystery_audit_score or 0
            data["satisfaction_score"] = quarter_sub.satisfaction_score or 0

    return data


# ============================================================
# GET ALL BRANCHES' IT DATA
# ============================================================

@app.get("/api/it/all")
def get_all_it_submissions_for_month(
    month: Optional[str] = None,
    report_month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return all IT submissions for the requested month.

    Supports both:
        /api/it/all?month=2026-08
        /api/it/all?report_month=2026-08

    This matches the frontend fetch calls and also applies the
    quarter-start values for quarterly fields when required.
    """

    selected_month = (month or report_month or "").strip()

    if not selected_month:
        raise HTTPException(
            status_code=400,
            detail="Month is required. Use YYYY-MM."
        )

    parsed_month = parse_month(selected_month)

    subs = (
        db.query(ITSubmission)
        .join(Branch, ITSubmission.branch_id == Branch.id)
        .filter(
            ITSubmission.report_month == parsed_month
        )
        .order_by(Branch.name)
        .all()
    )

    results = []

    for it_sub in subs:
        data = submission_to_dict(it_sub)

        # For non-quarter months, use the quarter-start submission
        # for the quarterly fields.
        quarter_start = get_quarter_start_month(parsed_month)

        if parsed_month != quarter_start:
            quarter_sub = (
                db.query(ITSubmission)
                .filter(
                    ITSubmission.branch_id == it_sub.branch_id,
                    ITSubmission.report_month == quarter_start,
                )
                .first()
            )

            if quarter_sub:
                data["branding_compliance"] = (
                    quarter_sub.branding_compliance or 0
                )
                data["mystery_audit_score"] = (
                    quarter_sub.mystery_audit_score or 0
                )
                data["satisfaction_score"] = (
                    quarter_sub.satisfaction_score or 0
                )

        results.append(data)

    return results


# ============================================================
# DELETE SAVED IT DATA
# ============================================================

@app.delete("/api/it/submission")
def delete_it_submission(
    branch: str,
    month: str,
    db: Session = Depends(get_db),
):
    branch_obj = (
        db.query(Branch)
        .filter(Branch.name == branch)
        .first()
    )

    if not branch_obj:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    report_month = parse_month(month)

    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch_obj.id,
            ITSubmission.report_month == report_month,
        )
        .first()
    )

    if not it_sub:
        raise HTTPException(
            status_code=404,
            detail=(
                "No saved IT data found "
                "for this branch and month."
            ),
        )

    score_row = (
        db.query(MonthlyScore)
        .filter(
            MonthlyScore.branch_id == branch_obj.id,
            MonthlyScore.report_month == report_month,
        )
        .first()
    )

    try:
        db.delete(it_sub)

        if score_row:
            db.delete(score_row)

        db.commit()

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unable to delete data: {str(exc)}",
        )

    return {
        "status": "ok",
        "message": "Saved IT data deleted successfully.",
    }


# ============================================================
# RECALCULATE SCORE
# ============================================================

def _recalculate_score(
    db: Session,
    branch_id: int,
    report_month: date,
):
    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch_id,
            ITSubmission.report_month == report_month,
        )
        .first()
    )

    if not it_sub:
        return

    # Fetch quarter-start submission if different
    quarter_start = get_quarter_start_month(report_month)
    quarter_sub = None
    if report_month != quarter_start:
        quarter_sub = (
            db.query(ITSubmission)
            .filter(
                ITSubmission.branch_id == branch_id,
                ITSubmission.report_month == quarter_start,
            )
            .first()
        )

    result = compute_full_score(
        it_sub,
        None,          # acc_sub not used
        quarter_sub,   # pass quarter submission
    )

    score_row = (
        db.query(MonthlyScore)
        .filter(
            MonthlyScore.branch_id == branch_id,
            MonthlyScore.report_month == report_month,
        )
        .first()
    )

    if not score_row:
        score_row = MonthlyScore(
            branch_id=branch_id,
            report_month=report_month,
        )
        db.add(score_row)

    score_row.financial_health = int(round(result.get("financial_health", 0)))
    score_row.student_growth = int(round(result.get("student_growth", 0)))
    score_row.operations_discipline = int(round(result.get("operations_discipline", 0)))
    score_row.brand_quality = int(round(result.get("brand_quality", 0)))
    score_row.customer_experience = int(round(result.get("customer_experience", 0)))
    score_row.local_marketing = int(round(result.get("local_marketing", 0)))
    score_row.base_score = int(round(result.get("base_score", 0)))
    score_row.penalty = int(round(result.get("penalty", 0)))
    score_row.final_score = int(round(result.get("final_score", 0)))
    score_row.rating = result.get("rating", "Critical")
    score_row.action = result.get("action", "")

    db.commit()


# ============================================================
# DASHBOARD — SINGLE BRANCH
# ============================================================

@app.get("/api/dashboard/branch/{branch_name}")
def get_branch_score(
    branch_name: str,
    month: str,
    db: Session = Depends(get_db),
):
    branch = (
        db.query(Branch)
        .filter(Branch.name == branch_name)
        .first()
    )

    if not branch:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    report_month = parse_month(month)

    score = (
        db.query(MonthlyScore)
        .filter(
            MonthlyScore.branch_id == branch.id,
            MonthlyScore.report_month == report_month,
        )
        .first()
    )

    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch.id,
            ITSubmission.report_month == report_month,
        )
        .first()
    )

    data = {
        "branch": branch_name,
        "month": month,
    }

    data.update(
        _score_dict(score)
    )

    data.update(
        compute_submetrics(it_sub)
    )

    return data


# ============================================================
# DASHBOARD — ALL BRANCHES
# ============================================================

@app.get("/api/dashboard/all")
def get_all_scores(
    month: str,
    db: Session = Depends(get_db),
):
    report_month = parse_month(month)

    rows = (
        db.query(Branch, MonthlyScore)
        .join(
            MonthlyScore,
            MonthlyScore.branch_id == Branch.id,
        )
        .filter(
            MonthlyScore.report_month == report_month
        )
        .order_by(
            MonthlyScore.final_score.desc()
        )
        .all()
    )

    it_subs_for_month = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.report_month == report_month
        )
        .all()
    )
    it_subs_by_branch: Dict[int, ITSubmission] = {
        it_sub.branch_id: it_sub for it_sub in it_subs_for_month
    }

    results = []

    for branch, score in rows:
        row = {
            "branch": branch.name,
            "final_score": int(round(score.final_score or 0)),
            "rating": score.rating or "No Data",
            "action": score.action or "",
            "financial_health": int(round(score.financial_health or 0)),
            "student_growth": int(round(score.student_growth or 0)),
            "operations_discipline": int(round(score.operations_discipline or 0)),
            "brand_quality": int(round(score.brand_quality or 0)),
            "customer_experience": int(round(score.customer_experience or 0)),
            "local_marketing": int(round(score.local_marketing or 0)),
            "base_score": int(round(score.base_score or 0)),
            "penalty": int(round(score.penalty or 0)),
        }

        it_sub = it_subs_by_branch.get(branch.id)
        row.update(compute_submetrics(it_sub))

        results.append(row)

    return results


# ============================================================
# EXPORT — SINGLE BRANCH, SINGLE MONTH
# ============================================================

@app.get("/api/export/branch/{branch_name}")
def export_branch_month(
    branch_name: str,
    month: str,
    db: Session = Depends(get_db),
):
    branch = (
        db.query(Branch)
        .filter(Branch.name == branch_name)
        .first()
    )

    if not branch:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    report_month = parse_month(month)

    it_sub = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch.id,
            ITSubmission.report_month == report_month,
        )
        .first()
    )

    score = (
        db.query(MonthlyScore)
        .filter(
            MonthlyScore.branch_id == branch.id,
            MonthlyScore.report_month == report_month,
        )
        .first()
    )

    if it_sub:
        data = submission_to_dict(it_sub)
    else:
        data = {
            "branch": branch_name,
            "report_month": month,
        }

    data.update(
        _score_dict(score)
    )

    return data


# ============================================================
# EXPORT — ALL BRANCHES, SINGLE MONTH
# ============================================================

@app.get("/api/export/all")
def export_all_branches(
    month: str,
    db: Session = Depends(get_db),
):
    report_month = parse_month(month)

    results = []

    branches = (
        db.query(Branch)
        .order_by(Branch.name)
        .all()
    )

    for branch in branches:
        it_sub = (
            db.query(ITSubmission)
            .filter(
                ITSubmission.branch_id == branch.id,
                ITSubmission.report_month == report_month,
            )
            .first()
        )

        score = (
            db.query(MonthlyScore)
            .filter(
                MonthlyScore.branch_id == branch.id,
                MonthlyScore.report_month == report_month,
            )
            .first()
        )

        if it_sub:
            data = submission_to_dict(it_sub)
        else:
            data = {
                "branch": branch.name,
                "report_month": month,
            }

        data.update(
            _score_dict(score)
        )

        results.append(data)

    return results


# ============================================================
# EXPORT — SINGLE BRANCH, ALL MONTHS
# ============================================================

@app.get("/api/export/branch/{branch_name}/history")
def export_branch_history(
    branch_name: str,
    db: Session = Depends(get_db),
):
    branch = (
        db.query(Branch)
        .filter(Branch.name == branch_name)
        .first()
    )

    if not branch:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    subs = (
        db.query(ITSubmission)
        .filter(
            ITSubmission.branch_id == branch.id
        )
        .order_by(
            ITSubmission.report_month
        )
        .all()
    )

    results = []

    for it_sub in subs:
        data = submission_to_dict(it_sub)

        score = (
            db.query(MonthlyScore)
            .filter(
                MonthlyScore.branch_id == branch.id,
                MonthlyScore.report_month == (
                    it_sub.report_month
                ),
            )
            .first()
        )

        data.update(
            _score_dict(score)
        )

        results.append(data)

    return results


# ============================================================
# BRANCH LIST API
# ============================================================

@app.get("/api/branches")
def get_branches(
    db: Session = Depends(get_db),
):
    branches = (
        db.query(Branch)
        .order_by(Branch.name)
        .all()
    )

    return {
        "count": len(branches),
        "branches": [
            {
                "id": branch.id,
                "name": branch.name,
            }
            for branch in branches
        ],
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "RAACK Scorify",
        "version": "1.0.0",
    }


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)