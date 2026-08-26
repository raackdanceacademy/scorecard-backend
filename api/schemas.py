from pydantic import BaseModel

class ITSubmissionIn(BaseModel):
    branch: str
    report_month: str

    # ===== Operations Discipline =====
    # REMOVED: classes_planned, classes_conducted, trainer_attendance
    attendance_recording: float
    crm_usage: float
    report_submission: float

    # ===== Brand & Quality Compliance =====
    # REMOVED: hygiene_score, curriculum_compliance, trainer_certification
    branding_compliance: float
    mystery_audit_score: float

    # ===== Customer Experience =====
    satisfaction_score: float
    google_rating: float
    complaints_received: int
    complaints_resolved: int
    referrals: int
    event_satisfaction: float

    # ===== Financial Health =====
    revenue_target: float
    revenue_actual: float
    tshirt_due: float = 0
    tshirt_paid: float = 0
    salary_due: float = 0
    salary_paid: float = 0
    hotel_due: float = 0
    hotel_paid: float = 0
    merch_due: float = 0
    merch_paid: float = 0
    fee_collection_rate: float
    operating_margin: float = 0

    # ===== Student Growth & Retention =====
    opening_students: int = 0
    new_student_target: int = 0
    new_enrollments: int
    dropouts: int
    closing_students: int = 0
    # REMOVED: batch_utilization, trials_conducted, trial_conversions

    # ===== Local Marketing & Community =====
    marketing_activities: int = 0
    partnerships: int = 0
    # REMOVED: social_media_posts, events_workshops

    # ===== Penalty Flags =====
    unauthorized_discount: str = 'No'
    false_reporting: str = 'No'
    trainer_misconduct: str = 'No'
    comments: str = ''