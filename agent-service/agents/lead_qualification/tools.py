from langchain_core.tools import tool
from datetime import datetime
from typing import Optional
import re


@tool
def check_eligibility_criteria(state: dict) -> dict:
    """
    Deterministic eligibility checks against policy rules.
    Returns passed checks, failed checks, and disqualification reasons.
    Run BEFORE calling Claude.
    """
    passed = []
    failed = []
    reasons = []

    # ── 1. Full name present ──────────────────────────────────────────────────
    full_name = (state.get("full_name", "") or "").strip()
    if len(full_name) >= 2:
        passed.append("full_name")
    else:
        failed.append("full_name")
        reasons.append("Applicant full name is missing")

    # ── 2. Lead score ─────────────────────────────────────────────────────────
    lead_score = state.get("lead_score", 0) or 0
    if lead_score >= 30:
        passed.append("lead_score")
    else:
        failed.append("lead_score")
        reasons.append(f"Lead score {lead_score:.0f} below minimum 30")

    # ── 3. PAN format ─────────────────────────────────────────────────────────
    pan = (state.get("pan_number", "") or "").upper()
    if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
        passed.append("pan_number")
    else:
        failed.append("pan_number")
        reasons.append(f"PAN {pan!r} missing or invalid format")

    # ── 4. Phone ──────────────────────────────────────────────────────────────
    phone = state.get("phone", "") or ""
    pc = re.sub(r"[\s\+\-]", "", phone)
    if pc.startswith("91") and len(pc) == 12:
        pc = pc[2:]
    if re.fullmatch(r"[6-9]\d{9}", pc):
        passed.append("phone")
    else:
        failed.append("phone")
        reasons.append(f"Mobile {phone!r} missing or invalid")

    # ── 5. Age ────────────────────────────────────────────────────────────────
    dob = state.get("date_of_birth")
    employment_type = (state.get("employment_type",
                       "salaried") or "salaried").lower()
    age = calculate_age(dob)

    if age is not None:
        max_age = 65 if employment_type == "self_employed" else 60
        if age < 21:
            failed.append("age_too_young")
            reasons.append(f"Applicant age {age} is below minimum 21")
        elif age > max_age:
            failed.append("age_too_old")
            reasons.append(
                f"Applicant age {age} exceeds maximum {max_age} "
                f"for {employment_type}"
            )
        else:
            passed.append("age")
    else:
        # DOB not provided — let Claude flag it
        passed.append("age_not_provided")

    # ── 6. Loan amount limits ─────────────────────────────────────────────────
    loan_amount = state.get("loan_amount", 0) or 0
    if loan_amount < 10_000:
        failed.append("loan_amount_min")
        reasons.append(f"Loan Rs.{loan_amount:,.0f} below minimum Rs.10,000")
    elif loan_amount > 5_000_000:
        failed.append("loan_amount_max")
        reasons.append(
            f"Loan Rs.{loan_amount:,.0f} exceeds maximum Rs.50,00,000")
    else:
        passed.append("loan_amount")

    # ── 7. Income threshold ───────────────────────────────────────────────────
    monthly_income = state.get("monthly_income", 0) or 0
    if monthly_income > 0:
        threshold = 50_000 if employment_type == "self_employed" else 30_000
        if monthly_income >= threshold:
            passed.append("monthly_income")
        else:
            failed.append("monthly_income")
            reasons.append(
                f"Income Rs.{monthly_income:,.0f} below threshold "
                f"Rs.{threshold:,.0f} for {employment_type}"
            )
    else:
        # Income not provided — Claude will assess
        passed.append("monthly_income_not_provided")

    # ── 8. Loan to income ratio ───────────────────────────────────────────────
    if monthly_income > 0 and loan_amount > 0:
        ratio = loan_amount / monthly_income
        if ratio <= 10:
            passed.append("loan_to_income_ratio")
        else:
            failed.append("loan_to_income_ratio")
            reasons.append(
                f"Loan is {ratio:.1f}x monthly income — max allowed is 10x"
            )

    # ── 9. Loan purpose ───────────────────────────────────────────────────────
    rejected_purposes = ["gambling", "speculative", "crypto", "illegal"]
    purpose = (state.get("loan_purpose", "") or "").lower()
    if any(rp in purpose for rp in rejected_purposes):
        failed.append("loan_purpose")
        reasons.append(f"Loan purpose '{purpose}' is not permitted")
    else:
        passed.append("loan_purpose")

    return {
        "passed":                   passed,
        "failed":                   failed,
        "disqualification_reasons": reasons,
        "hard_fail":                len(failed) > 0,
        "checks_run":               len(passed) + len(failed),
    }


@tool
def calculate_age(date_of_birth: str) -> Optional[int]:
    """Calculate age from date string. Returns None if cannot parse."""
    if not date_of_birth:
        return None
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            dob = datetime.strptime(date_of_birth, fmt)
            today = datetime.today()
            return today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
        except ValueError:
            continue
    return None


@tool
def query_eligibility_policy(query: str) -> str:
    """RAG query to retrieve relevant eligibility policy from pgvector."""
    # TODO: Embed query, similarity search on compliance_policies collection
    pass
