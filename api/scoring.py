from datetime import date

def safe_div(a, b, if_zero=0.0):
    """Safe division, returns if_zero when b is zero."""
    return a / b if b else if_zero


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


def compute_financial_health(data):
    """Max 225 — unchanged"""
    revenue_ratio = safe_div(data['actual_revenue'], data['target_revenue'], 0)

    total_due = data['tshirt_due'] + data['salary_due'] + data['hotel_due'] + data['merch_due']
    total_paid = data['tshirt_paid'] + data['salary_paid'] + data['hotel_paid'] + data['merch_paid']
    payment_ratio = min(safe_div(total_paid, total_due, 1), 1)
    payment_shortfall = max(0, total_due - total_paid)

    financial_health = 225 * (
        0.35 * min(revenue_ratio, 1.2) / 1.2 +
        0.25 * payment_ratio +
        0.15 * data['fee_collection_pct'] +
        0.15 * min(safe_div(data['operating_margin'], 0.25, 0), 1) +
        0.10 * (1 if total_due == 0 else max(0, 1 - payment_shortfall / total_due))
    )

    return round(financial_health)


def compute_student_growth(data):
    """Max 225 — new weights: 0.43, 0.49, 0.08"""
    opening = data['opening_students']
    new_students = data['new_students']
    dropouts = data['dropouts']

    retention_rate = safe_div(
        opening + new_students - dropouts,
        max(1, opening + new_students),
        0
    )
    dropout_rate = safe_div(dropouts, max(1, opening + new_students), 0)

    student_growth = 225 * (
        0.43 * min(safe_div(data['new_students'], max(1, data['new_student_target']), 0), 1.2) / 1.2 +
        0.49 * retention_rate +
        0.08 * max(0, 1 - dropout_rate / 0.15)
    )

    return round(student_growth)


def compute_operations_discipline(data):
    """Max 135 — new weights: 0.44, 0.33, 0.22"""
    operations_discipline = 135 * (
        0.44 * data['attendance_recording'] +
        0.33 * data['crm_usage'] +
        0.22 * data['report_submission']
    )
    return round(operations_discipline)


def compute_brand_quality(data):
    """Max 70 — new weights: 0.33, 0.67"""
    brand_quality = 70 * (
        0.33 * data['branding_compliance'] +
        0.67 * data['mystery_audit_score']
    )
    return round(brand_quality)


def compute_customer_experience(data):
    """Max 70 — unchanged"""
    complaint_resolution_rate = min(safe_div(data['complaints_resolved'], data['complaints_received'], 1), 1)

    customer_experience = 70 * (
        0.35 * data['satisfaction_score'] +
        0.20 * min(data['google_rating'] / 5, 1) +
        0.20 * complaint_resolution_rate +
        0.15 * min(data['referrals'] / 10, 1) +
        0.10 * data['event_satisfaction']
    )

    return round(customer_experience)


def compute_local_marketing(data):
    """Max 175 — new weights: 0.67, 0.33"""
    local_marketing = 175 * (
        0.67 * min(data['marketing_activities'] / 8, 1) +
        0.33 * min(data['partnerships'] / 4, 1)
    )
    return round(local_marketing)


def compute_penalties(data):
    """Penalty — removed hygiene & curriculum checks"""
    penalty = 0

    total_due = data['tshirt_due'] + data['salary_due'] + data['hotel_due'] + data['merch_due']
    total_paid = data['tshirt_paid'] + data['salary_paid'] + data['hotel_paid'] + data['merch_paid']
    payment_ratio = min(safe_div(total_paid, total_due, 1), 1)
    payment_shortfall = max(0, total_due - total_paid)
    complaint_resolution_rate = min(safe_div(data['complaints_resolved'], data['complaints_received'], 1), 1)

    if payment_ratio < 0.75:
        penalty += 20
    if total_due > 0 and safe_div(payment_shortfall, total_due, 0) > 0.25:
        penalty += 15
    if data.get('unauthorized_discount', 'No') == 'Yes':
        penalty += 20
    if data.get('complaints_received', 0) > 0 and complaint_resolution_rate < 0.7:
        penalty += 15
    if data.get('false_reporting', 'No') == 'Yes':
        penalty += 50
    if data.get('trainer_misconduct', 'No') == 'Yes':
        penalty += 40

    return penalty


def compute_rating(final_score):
    if final_score >= 800:
        return "Excellent"
    if final_score >= 700:
        return "Good"
    if final_score >= 600:
        return "Watchlist"
    if final_score >= 500:
        return "Risky"
    return "Critical"


def compute_action(final_score):
    if final_score < 500:
        return "Critical intervention"
    if final_score < 600:
        return "Immediate support"
    if final_score < 700:
        return "Watch closely"
    if final_score < 800:
        return "Coach selectively"
    return "Expansion candidate"


def compute_full_score(it_sub, acc_sub=None, quarter_sub=None):
    """
    Calculate the full score using data from IT submission.
    If quarter_sub is provided and the current month is not a quarter-start month,
    the quarterly fields (branding_compliance, mystery_audit_score, satisfaction_score)
    are taken from the quarter-start submission.
    """
    # Determine if current month is a quarter start
    current_month = it_sub.report_month
    quarter_start = get_quarter_start_month(current_month)
    is_quarter_start = (current_month == quarter_start)

    # Use quarter_sub values for the three fields if applicable
    if quarter_sub and not is_quarter_start:
        branding = quarter_sub.branding_compliance or 0
        mystery = quarter_sub.mystery_audit_score or 0
        satisfaction = quarter_sub.satisfaction_score or 0
    else:
        branding = it_sub.branding_compliance or 0
        mystery = it_sub.mystery_audit_score or 0
        satisfaction = it_sub.satisfaction_score or 0

    # Build data dictionary
    data = {
        # Operations
        'attendance_recording': it_sub.attendance_recording or 0,
        'crm_usage': it_sub.crm_usage or 0,
        'report_submission': it_sub.report_submission or 0,

        # Brand & Quality (with quarterly overrides)
        'branding_compliance': branding,
        'mystery_audit_score': mystery,

        # Customer Experience
        'satisfaction_score': satisfaction,
        'google_rating': it_sub.google_rating or 0,
        'complaints_received': it_sub.complaints_received or 0,
        'complaints_resolved': it_sub.complaints_resolved or 0,
        'referrals': it_sub.referrals or 0,
        'event_satisfaction': it_sub.event_satisfaction or 0,

        # Financial Health
        'target_revenue': it_sub.revenue_target or 0,
        'actual_revenue': it_sub.revenue_actual or 0,
        'tshirt_due': it_sub.tshirt_due or 0,
        'tshirt_paid': it_sub.tshirt_paid or 0,
        'salary_due': it_sub.salary_due or 0,
        'salary_paid': it_sub.salary_paid or 0,
        'hotel_due': it_sub.hotel_due or 0,
        'hotel_paid': it_sub.hotel_paid or 0,
        'merch_due': it_sub.merch_due or 0,
        'merch_paid': it_sub.merch_paid or 0,
        'fee_collection_pct': it_sub.fee_collection_rate or 0,
        'operating_margin': it_sub.operating_margin or 0,

        # Student Growth
        'opening_students': it_sub.opening_students or 0,
        'new_student_target': it_sub.new_student_target or 0,
        'new_students': it_sub.new_enrollments or 0,
        'dropouts': it_sub.dropouts or 0,

        # Local Marketing
        'marketing_activities': it_sub.marketing_activities or 0,
        'partnerships': it_sub.partnerships or 0,

        # Penalty Flags
        'unauthorized_discount': it_sub.unauthorized_discount or "No",
        'false_reporting': it_sub.false_reporting or "No",
        'trainer_misconduct': it_sub.trainer_misconduct or "No",
    }

    # Calculate all scores
    financial_health = compute_financial_health(data)
    student_growth = compute_student_growth(data)
    operations_discipline = compute_operations_discipline(data)
    brand_quality = compute_brand_quality(data)
    customer_experience = compute_customer_experience(data)
    local_marketing = compute_local_marketing(data)

    base_score = (financial_health + student_growth + operations_discipline +
                  brand_quality + customer_experience + local_marketing)

    penalty = compute_penalties(data)
    final_score = round(max(0, min(900, base_score - penalty)))

    return {
        "financial_health": financial_health,
        "student_growth": student_growth,
        "operations_discipline": operations_discipline,
        "brand_quality": brand_quality,
        "customer_experience": customer_experience,
        "local_marketing": local_marketing,
        "base_score": round(base_score),
        "penalty": penalty,
        "final_score": final_score,
        "rating": compute_rating(final_score),
        "action": compute_action(final_score),
    }