from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base   # ✅ Fixed: added the dot for relative import

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    access_code = Column(String(20), unique=True, nullable=False)


class ITSubmission(Base):
    __tablename__ = "it_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    report_month = Column(Date, nullable=False)

    # ---------- Operations ----------
    # REMOVED: classes_planned, classes_conducted, trainer_attendance
    attendance_recording = Column(Float, nullable=True)
    crm_usage = Column(Float, nullable=True)
    report_submission = Column(Float, nullable=True)

    # ---------- Brand & Quality ----------
    # REMOVED: hygiene_score, curriculum_compliance, trainer_certification
    branding_compliance = Column(Float, nullable=True)
    mystery_audit_score = Column(Float, nullable=True)

    # ---------- Customer Experience ----------
    satisfaction_score = Column(Float, nullable=True)
    google_rating = Column(Float, nullable=True)
    complaints_received = Column(Integer, nullable=True)
    complaints_resolved = Column(Integer, nullable=True)
    referrals = Column(Integer, nullable=True)
    event_satisfaction = Column(Float, nullable=True)

    # ---------- Financial Health ----------
    revenue_target = Column(Float, nullable=True)
    revenue_actual = Column(Float, nullable=True)
    tshirt_due = Column(Float, nullable=True)
    tshirt_paid = Column(Float, nullable=True)
    salary_due = Column(Float, nullable=True)
    salary_paid = Column(Float, nullable=True)
    hotel_due = Column(Float, nullable=True)
    hotel_paid = Column(Float, nullable=True)
    merch_due = Column(Float, nullable=True)
    merch_paid = Column(Float, nullable=True)
    fee_collection_rate = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)

    # ---------- Student Growth ----------
    opening_students = Column(Integer, nullable=True)
    new_student_target = Column(Integer, nullable=True)
    new_enrollments = Column(Integer, nullable=True)
    dropouts = Column(Integer, nullable=True)
    closing_students = Column(Integer, nullable=True)
    # REMOVED: batch_utilization, trials_conducted, trial_conversions

    # ---------- Local Marketing ----------
    marketing_activities = Column(Integer, nullable=True)
    partnerships = Column(Integer, nullable=True)
    # REMOVED: social_media_posts, events_workshops

    # ---------- Penalty Flags ----------
    unauthorized_discount = Column(String(10), nullable=True, default="No")
    false_reporting = Column(String(10), nullable=True, default="No")
    trainer_misconduct = Column(String(10), nullable=True, default="No")
    comments = Column(String(500), nullable=True)

    submitted_at = Column(DateTime, server_default=func.now())


class MonthlyScore(Base):
    __tablename__ = "monthly_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    report_month = Column(Date, nullable=False)

    financial_health = Column(Integer, nullable=True)
    student_growth = Column(Integer, nullable=True)
    operations_discipline = Column(Integer, nullable=True)
    brand_quality = Column(Integer, nullable=True)
    customer_experience = Column(Integer, nullable=True)
    local_marketing = Column(Integer, nullable=True)
    base_score = Column(Integer, nullable=True)
    penalty = Column(Integer, nullable=True)
    final_score = Column(Integer, nullable=True)
    rating = Column(String(50), nullable=True)
    action = Column(String(100), nullable=True)