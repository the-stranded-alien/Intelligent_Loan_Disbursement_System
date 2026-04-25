# LoanFlow — Test Execution Report

> **How to use:** Paste `test-prompt.txt` into the Claude Chrome extension (or any Claude session with browser access) while the app is open. Claude will execute each test and fill in the Actual / Status columns below.

**Date:** _fill after test run_
**Tester:** _fill after test run_
**Base URL:** _fill after test run_
**Commit:** _fill after test run (`git rev-parse --short HEAD`)_

---

## Summary

| Category | Tests | ✅ Pass | ❌ Fail | ⚠️ Partial | ⏭️ Skip |
|----------|-------|--------|--------|-----------|--------|
| 1. Infrastructure | 3 | | | | |
| 2. Application Submission | 4 | | | | |
| 3. Status Tracker | 6 | | | | |
| 4. RM Dashboard | 6 | | | | |
| 5. Assessment Chat | 5 | | | | |
| 6. Document Upload | 2 | | | | |
| 7. Applications List | 2 | | | | |
| 8. Analytics | 5 | | | | |
| 9. Agent Activity | 2 | | | | |
| 10. Known Gaps (verified) | 3 | | | | |
| **TOTAL** | **38** | | | | |

---

## Section 1 — Infrastructure

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 1.1 | `GET /health` | `{"status":"ok"}` | | | |
| 1.2 | `GET /api/v1/analytics/overview` | JSON with counts | | | |
| 1.3 | `GET /api/v1/analytics/background-agents` | JSON with 4 sections | | | |

---

## Section 2 — Application Submission

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 2.1 | Apply page renders | 2-step form visible | | | |
| 2.2 | Form validation | Errors on empty/invalid fields | | | |
| 2.3 | Submit small loan (₹1.5L) | Returns application_id, redirects to status | | | **SMALL_APP_ID:** |
| 2.4 | Submit large loan (₹5L) | Returns application_id | | | **LARGE_APP_ID:** |

---

## Section 3 — Status Tracker & Pipeline

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 3.1 | Search by app ID | Applicant card visible | | | |
| 3.2 | Eligibility banner | Green eligible or red ineligible banner | | | |
| 3.3 | Pipeline stage progression | `current_stage` advances after ~60s | | | |
| 3.4 | ART offers card | 3 options A/B/C with rates + recommended badge | | | |
| 3.5 | Live WebSocket | NotificationFeed shows connected + live events | | | |
| 3.6 | Copy ID button | Copies UUID to clipboard | | | |

---

## Section 4 — RM Dashboard

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 4.1 | `GET /api/v1/rm/queue` | Array of pending_review apps | | | |
| 4.2 | `GET /api/v1/rm/:id/context` | application + audit_trail | | | |
| 4.3 | Negotiation advice | recommended_option, risk_analysis, DTI | | | Requires art_negotiation complete |
| 4.4 | Counter-offer simulator | monthly_emi, total_payable, interest | | | |
| 4.5 | RM submit approve | `{"decision":"approve","status":"approved"}` | | | |
| 4.6 | NegotiationPanel UI | Advice loads, simulator inputs visible | | | |

---

## Section 5 — Assessment Chat

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 5.1 | Start session via API | session_id + Priya's opening message | | | **SESSION_ID:** |
| 5.2 | GET session metadata | session_id, application_id, opening | | | |
| 5.3 | Assessment page renders | Priya's greeting visible, input enabled | | | |
| 5.4 | Chat through 5 questions | Priya responds to each, `is_complete: true` after Q5 | | | |
| 5.5 | Finalize assessment | repayment_confidence, recommendation, risk_flags | | | |

---

## Section 6 — Document Upload

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 6.1 | Upload salary slip | document_id, status: pending | | | |
| 6.2 | List documents | Array containing uploaded document | | | |

---

## Section 7 — Applications List

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 7.1 | Page renders with data | Both test apps visible in list | | | |
| 7.2 | Status badges | Human-readable badges for all statuses | | | |

---

## Section 8 — Analytics

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 8.1 | Overview counts | total, approved, rejected, pending, approval_rate | | | |
| 8.2 | Pipeline breakdown | 7-stage array | | | |
| 8.3 | Agent rejection rates | stages + pending_hitl + avg_loan | | | |
| 8.4 | Disbursement metrics | total_disbursed, total_amount, avg | | | |
| 8.5 | Analytics UI | All cards render, no blank sections | | | |

---

## Section 9 — Agent Activity

| ID | Test | Expected | Actual | Status | Notes |
|----|------|----------|--------|--------|-------|
| 9.1 | Background agents API | monitoring, outreach, pipeline, assessment | | | |
| 9.2 | Agents page UI | All 4 sections visible with counts | | | |

---

## Section 10 — Known Gaps (Verify Current Behaviour)

These are **documented incomplete features**. The test verifies they fail gracefully rather than crash.

| ID | Gap | Expected Current Behaviour | Actual | Confirmed | Notes |
|----|-----|---------------------------|--------|-----------|-------|
| 10.1 | Disbursement never triggered | status stays `completed`, never → `disbursed` | | | Fix: call `retry_disbursement.delay()` after pipeline.completed |
| 10.2 | Assessment result not saved | app status unchanged after finalize | | | Fix: write to AuditLog + update status in finalize_assessment |
| 10.3 | Webhook callback | `{"received":true}`, no crash | | | Passive endpoint only |

---

## Issues Found

> _Fill after test run. Only list unexpected failures — things that should work but don't._

| # | Section | Test ID | Description | Severity |
|---|---------|---------|-------------|----------|
| 1 | | | | |
| 2 | | | | |

---

## Known Gaps — Engineering Backlog

These are documented in `FinalPlan.md` and are **not regressions**. They require targeted fixes:

| Priority | Gap | File(s) to Change | Effort |
|----------|-----|-------------------|--------|
| 🔴 Critical | Disbursement never triggered — `retry_disbursement.delay()` never called | `agent-service/worker/tasks.py` lines 91–92, 155–156 | ~10 min |
| 🔴 Critical | Assessment result discarded — `finalize_assessment` writes nothing to DB | `backend-api/routers/assessment_proxy.py` line 201 | ~20 min |
| 🟡 Significant | RM `request_info` doesn't auto-create assessment session | `backend-api/routers/rm.py` line 131 | ~15 min |
| 🟡 Significant | No outcome notifications (approved/rejected/disbursed) to applicant | `backend-api/services/event_consumer.py` line 195 | ~20 min |
| 🟠 Backlog | `notification-service/consumers/event_consumer.py` is a stub | `notification-service/consumers/event_consumer.py` | ~1 hr |

---

## Environment Variables Checklist (Railway)

| Variable | Service | Required For | Set? |
|----------|---------|-------------|------|
| `DATABASE_URL` | backend-api | All DB operations | |
| `REDIS_STREAMS_URL` | backend-api, agent-service | Event bus | |
| `REDIS_CELERY_URL` | agent-service | Celery workers + Beat | |
| `ANTHROPIC_API_KEY` | backend-api, agent-service | All LLM calls | |
| `SENDGRID_API_KEY` | notification-service | Email notifications | |
| `TWILIO_ACCOUNT_SID` | notification-service | SMS/WhatsApp | |
| `TWILIO_AUTH_TOKEN` | notification-service | SMS/WhatsApp | |

---

## Verdict

> _Fill after test run._

**Demo-ready:** Yes / No
**Blocks production:**
- [ ] DATABASE_URL configured
- [ ] REDIS URLs configured
- [ ] ANTHROPIC_API_KEY configured
- [ ] Disbursement trigger fix (10 min)
- [ ] Assessment result persistence fix (20 min)

**Overall health:** _/10
