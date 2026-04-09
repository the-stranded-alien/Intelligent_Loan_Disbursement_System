# Final Plan — Intelligent Loan Disbursement System

## Status as of 2026-04-09

Core 7-node pipeline is working end-to-end with live WebSocket updates on the UI.
This document covers all remaining work: pipeline refinements, new background agents,
and frontend improvements.

---

## Part 1 — Pipeline Node Refinements

### Node 1: Lead Gen (Lead Capture)

**Current state:** Validates web form fields via LLM. Outputs eligible/ineligible.

**Required changes:**

1. **Minimum loan amount** — Change form validation from ₹10,000 → ₹1,000
   - File: `frontend/src/pages/ApplicationForm.tsx` line 33
   - Change: `.min(10000, ...)` → `.min(1000, 'Minimum ₹1,000')`
   - File: `backend-api/routers/applications.py` — no DB constraint, form handles it

2. **Expand web form fields** — Add fields the LLM can validate at lead stage:
   - `city` (text) — for geographic risk
   - `state` (dropdown — Indian states)
   - `residential_status` (owned / rented / family) — stability signal
   - `years_at_current_address` (number)
   - `employer_name` (text, only if salaried/business)
   - `years_in_current_job` (number, only if salaried)
   - Add these to `ApplicationCreate` schema, `Application` DB model, and a new Alembic migration

3. **Node output — make eligibility explicit on UI:**
   - If `eligibility_result = ineligible`: show a clear rejection card with reason on StatusTracker
   - If `eligibility_result = eligible`: show "Eligible — KYC step next" green banner
   - The WorkflowTimeline stage dropdown already shows `eligibility_reason` — confirm it renders

4. **Email on eligibility (stub):**
   - When `node.completed` fires for `lead_capture` with `eligibility_result = eligible`:
     publish an event to `notification-service` → send email: "You are eligible, please complete KYC"
   - Files: `notification-service/tasks/` — add `send_eligibility_email` Celery task
   - Trigger: from `backend-api/services/event_consumer.py` on `stage.lead_capture.completed` audit event

**Implementation steps:**
```
1. Add new fields to Alembic migration (0006_add_lead_gen_fields.py)
2. Add columns to backend-api/db/models.py Application
3. Add fields to ApplicationCreate in routers/applications.py + schemas/application.py
4. Add fields to agent-service/graph/state.py ApplicationState
5. Update lead_capture prompt (config/prompts/lead_capture.j2) to evaluate new fields
6. Update ApplicationForm.tsx — add Step 1 fields, change min loan to ₹1,000
7. Add eligibility result banner to StatusTracker.tsx
8. Add send_eligibility_email task to notification-service
```

---

### Node 2: Lead Qualification (Document Verification)

**Current state:** LLM simulates document check. Outputs pass/fail/request_info.

**Required changes:**

1. **Clarify scope** — Node 2 is ONLY about documents (salary slips, ITR, bank statements).
   No KYC. No credit. Just: can we verify the income and employment claimed?

2. **Three outcomes (not two):**
   - `pass` — documents verified, proceed to KYC
   - `fail` — documents clearly invalid, reject
   - `request_info` — documents incomplete, ask applicant to re-upload
   - Currently the router only handles pass/fail → add `request_info` path in `graph/router.py`
   - When `request_info`: pipeline pauses, notifies applicant, waits for re-upload (stub for now — treat as fail)

3. **Update prompt** — `config/prompts/lead_qualification.j2`:
   - Emphasise: only document quality check, NOT creditworthiness
   - Output must include `document_issues: []` list of what is missing/invalid

**Implementation steps:**
```
1. Update lead_qualification.j2 prompt — clarify scope, add request_info guidance
2. Update router.py route_after_qualification — handle request_info → END with note
3. Update WorkflowTimeline STAGE_FIELDS for lead_qualification — add document_issues field display
```

---

### Node 3: Identity Verification (KYC)

**Current state:** Simulates PAN format check, name match, face/liveness. Outputs kyc_status.

**Required changes:**

1. **Inputs are now explicit:** PAN number + photo (image upload)
   - Add a document upload step to the web form after eligibility is confirmed
   - For now: form captures PAN number (already done), photo upload is a stub

2. **Clearer output contract:**
   - `verified` → PAN valid, name matches application → proceed to credit
   - `mismatch` → name on PAN differs → reject with reason
   - `failed` → PAN format invalid → reject

3. **No changes to agent code needed** — prompt and outputs are already correct.

---

### Node 4: Credit Assessment

**Current state:** LLM simulates CIBIL/Experian pull. Pure LLM output.

**Required changes:**

1. **Add mock CIBIL API tool:**
   - Create `agent-service/agents/credit_assessment/tools.py` → `mock_cibil_lookup(pan_number)`
   - Returns a deterministic-ish credit score based on PAN hash + random seed
   - This simulates: "Technical → Scheduler DB → API CIBIL → Yes/No"
   - The LLM calls this tool, gets the mock score, then makes the decision
   - Use Claude tool_use (function calling) instead of pure text prompt

2. **Per-applicant differentiated scoring** (the Shikha/Sahil/Mou example):
   - Different applicants get different rates based on CIBIL score
   - Shikha: 100000, 12%, 2 years (score ~780)
   - Sahil: 100000, 15%, 3 years (score ~650)
   - Mou: 100000, 14%, 3 years (score ~700)
   - The mock CIBIL tool must return varied scores so Node 5 (ART) produces varied offers

3. **Bank details input:**
   - PAN, bank account, salary slips → all passed to credit assessment node
   - These fields are already in ApplicationState — confirm prompt uses them all

**Implementation steps:**
```
1. Rewrite credit_assessment/tools.py — implement mock_cibil_lookup as @tool
2. Rewrite credit_assessment/agent.py — use client.messages.create with tools= parameter
   Parse tool_use block, inject CIBIL result into prompt context, then get final decision
3. Update credit_assessment.j2 — add section showing CIBIL tool output
4. Test with 3 applicants to verify differentiated scoring
```

---

### Node 5: ART + Negotiation

**Current state:** Generates 3 offers (A/B/C). Works correctly.

**What "Negotiation Agent" means:**
- The negotiation is the offer selection step
- For HITL (loans > ₹2L): RM reviews the 3 offers and picks one (or overrides)
- For auto (loans ≤ ₹2L): system auto-selects Option B
- The Negotiation Agent is the same as ART Node — already implemented

**No changes needed** unless we add a customer-facing offer selection UI (deferred).

---

### Nodes 6 & 7: e-NACH and E-Sign

**Current state:** Both working. Simulate NPCI mandate + Aadhaar e-sign.

**No changes needed** for core pipeline. These are terminal nodes.

---

## Part 2 — New Background Agents

These are standalone autonomous agents that run outside the main LangGraph pipeline.
They are triggered by schedules or events, not by form submissions.

---

### Agent A: Applications Monitoring Agent

**Purpose:** Watch all open applications. If an application has had no update in X hours/days,
flag it and hand it to the Outreach Agent.

**Trigger:** Celery Beat scheduled task — runs every hour.

**Logic:**
```
1. Query DB: SELECT * FROM applications WHERE status IN ('pending', 'processing', 'pending_review')
   AND updated_at < NOW() - INTERVAL 'X hours'
2. For each stale application:
   - Check if an outreach was already sent recently (audit_log check)
   - If not → publish event to trigger Outreach Agent
3. Configurable thresholds:
   - pending → stale after 2 hours
   - processing → stale after 30 minutes (pipeline stuck)
   - pending_review → stale after 24 hours (RM hasn't acted)
```

**Files to create:**
```
agent-service/agents/monitoring/agent.py      — run_monitoring_scan()
agent-service/worker/tasks.py                 — add monitoring_scan Celery task
agent-service/worker/celery_beat.py or similar — add beat schedule entry
```

**Implementation steps:**
```
1. Create agent-service/agents/monitoring/__init__.py
2. Create agent-service/agents/monitoring/agent.py:
   - async def run_monitoring_scan() -> list[dict]
   - Queries backend-api DB (same Postgres) for stale applications
   - Returns list of {application_id, status, hours_stale, last_stage}
3. Add @celery_app.task name="agent.monitoring_scan" in tasks.py
   - Calls run_monitoring_scan()
   - For each stale app: publishes "outreach.required" event to Redis Streams
4. Add to Celery Beat schedule: every 60 minutes
5. Add "outreach.required" handler in event_consumer.py → triggers outreach agent
```

---

### Agent B: Outreach Agent

**Purpose:** Takes one stale application at a time, generates a personalised follow-up
message based on applicant details and current stage, sends it (email/SMS), and schedules
follow-ups.

**Trigger:** `outreach.required` Redis Streams event (published by Monitoring Agent).

**Logic:**
```
1. Fetch application details + audit trail from DB
2. Determine outreach context:
   - Stage = lead_capture rejected → "You weren't eligible because X. Here's how to improve."
   - Stage = pending_review → "Your application is under review. An RM will contact you soon."
   - Stage = processing (stuck) → "We're still processing your documents. No action needed."
   - Stage = pending (never started) → "Complete your application to get funds in 24h."
3. LLM generates personalised email/SMS using applicant name, loan purpose, amount
4. Send via SendGrid (email) / Twilio (SMS) through notification-service
5. Log outreach in audit_log: event_type="outreach.sent"
6. Schedule follow-up: if no response in 2 days → outreach again (max 4 times)
```

**Files to create:**
```
agent-service/agents/outreach/__init__.py
agent-service/agents/outreach/agent.py        — run_outreach(application_id, context)
agent-service/config/prompts/outreach.j2      — Jinja2 prompt for message generation
notification-service/tasks/send_outreach.py   — Celery task: send email + SMS
```

**Prompt template outline (outreach.j2):**
```jinja2
You are a loan relationship manager. Write a personalised follow-up message.

Applicant: {{ full_name }}
Loan Amount: ₹{{ loan_amount }} for {{ loan_purpose }}
Current Stage: {{ current_stage }}
Days Since Last Update: {{ days_stale }}
Reason Stalled: {{ stall_reason }}

Write a warm, professional email subject and body. Be concise (under 150 words).
Do NOT reveal internal system details. Focus on next steps for the applicant.

JSON output:
{
  "subject": "...",
  "email_body": "...",
  "sms_text": "...",   // under 160 chars
  "urgency": "low|medium|high",
  "suggested_followup_days": 2
}
```

**Implementation steps:**
```
1. Create agent-service/agents/outreach/__init__.py + agent.py
2. Create config/prompts/outreach.j2
3. Add @celery_app.task name="agent.run_outreach" in tasks.py
4. Add "outreach.required" handler in event_consumer.py (backend-api)
   OR add a separate outreach consumer in agent-service/consumers/
5. Add follow-up scheduling: store next_followup_at in a new outreach_log table
   OR use Celery ETA: run_outreach.apply_async(eta=now + timedelta(days=2))
6. Cap at 4 follow-ups: check audit_log count before sending
7. Wire to notification-service SendGrid/Twilio tasks
```

---

### Agent C: Assessment Agent

**Purpose:** Engages the applicant in a chat conversation to assess their repayment capacity.
Acts as a loan advisor — asks targeted questions, evaluates answers, makes a recommendation.

**Trigger:** Manual (RM initiates from dashboard) or automatic after Node 2 `request_info`.

**Architecture:**
```
Frontend chat UI → WebSocket → backend-api /ws/assessment/{session_id}
                             → assessment agent (LLM multi-turn)
                             → streams responses back over WS
```

**LLM pattern:** Multi-turn conversation using Claude's `messages` array with history.
The agent has a system prompt defining its role, and each user message gets appended.
After N turns or a terminal signal, produces a structured assessment JSON.

**Assessment questions the agent asks:**
```
1. "What is your primary source of income?"
2. "Do you have any outstanding loans or credit card dues?"
3. "What will you use this loan for specifically?"
4. "How stable is your job/business? Any expected changes in 6 months?"
5. "Can you comfortably pay ₹X per month as EMI?" (where X = calculated from loan terms)
```

**Output:**
```json
{
  "repayment_confidence": "high|medium|low",
  "assessment_notes": "...",
  "recommendation": "approve|review|reject",
  "risk_flags": ["..."],
  "conversation_summary": "..."
}
```

**Files to create:**
```
agent-service/agents/assessment/__init__.py
agent-service/agents/assessment/agent.py      — AssessmentSession class
agent-service/config/prompts/assessment.j2    — system prompt
backend-api/routers/assessment.py             — REST + WS endpoints
frontend/src/pages/AssessmentChat.tsx         — Chat UI
frontend/src/components/ChatBubble.tsx        — Message bubble component
```

**AssessmentSession class:**
```python
class AssessmentSession:
    def __init__(self, application_id: str, applicant_data: dict):
        self.application_id = application_id
        self.history: list[dict] = []  # Claude messages format
        self.system_prompt = render_system_prompt(applicant_data)
        self.client = anthropic.AsyncAnthropic(...)
    
    async def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        response = await self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=self.system_prompt,
            messages=self.history,
        )
        assistant_msg = response.content[0].text
        self.history.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg
    
    async def finalize(self) -> dict:
        # Ask LLM to produce structured assessment based on conversation
        ...
```

**Implementation steps:**
```
1. Create agent-service/agents/assessment/__init__.py + agent.py
2. Create config/prompts/assessment.j2 (system prompt for the loan advisor persona)
3. Create backend-api/routers/assessment.py:
   - POST /api/v1/assessment/{application_id}/start → creates session, returns session_id
   - WS  /ws/assessment/{session_id} → streams chat turns
   - POST /api/v1/assessment/{session_id}/finalize → returns structured JSON result
4. Store active sessions in memory dict (backend-api) or Redis (for multi-instance)
5. Create frontend/src/pages/AssessmentChat.tsx:
   - Chat bubble UI
   - WS connection to /ws/assessment/{session_id}
   - Send/receive messages
   - "Finalize Assessment" button at end
6. Add route in App.tsx: /assessment/:applicationId
7. Add "Start Assessment" button in RMDashboard for pending_review applications
8. On finalize: save assessment result to audit_log, update ApplicationState
```

---

### Agent D: Negotiation Agent (Standalone)

**Purpose:** When HITL is triggered (art_negotiation for loans > ₹2L), the Negotiation Agent
assists the RM by: explaining each offer, simulating what happens if the applicant counter-offers,
and recommending the optimal terms.

**This is different from the ART Node** — ART generates offers, Negotiation Agent helps RM
decide which offer to approve and what terms to set.

**Trigger:** RM opens the review context for a `pending_review` application.

**Logic:**
```
1. RM views 3 offers (A/B/C) in RMDashboard
2. Negotiation Agent panel shows alongside:
   - "Why Option B is recommended"
   - "Risk if we go with Option C (higher EMI burden)"
   - "Counter-offer simulator: what if we offer 11% instead of 12%?"
3. RM clicks "Approve with Option B" → submits to /api/v1/rm/{id}/review
```

**Files to create/modify:**
```
agent-service/agents/negotiation/__init__.py
agent-service/agents/negotiation/agent.py     — run_negotiation_analysis(state)
agent-service/config/prompts/negotiation.j2
backend-api/routers/rm.py                     — add GET /{id}/negotiation-advice endpoint
frontend/src/components/NegotiationPanel.tsx  — show advice alongside RM review
```

**Implementation steps:**
```
1. Create agent-service/agents/negotiation/agent.py
   - Takes application state (offers, credit score, income, etc.)
   - Returns: recommended_option, risk_analysis, counter_offer_scenarios
2. Create backend-api/routers/rm.py endpoint GET /{id}/negotiation-advice
   - Calls agent-service (HTTP) or triggers Celery task to run negotiation analysis
   - Returns structured advice JSON
3. Create frontend/src/components/NegotiationPanel.tsx
   - Shows in RMDashboard alongside AgentDecisionCard
   - Displays: recommended offer, risk summary, counter-offer table
4. Add "Simulate Counter Offer" interactive input: RM types custom rate → agent re-calculates
```

---

## Part 3 — Frontend Remaining Work

### 3.1 ApplicationForm Updates

- [ ] Change min loan amount: ₹10,000 → ₹1,000
- [ ] Add Step 1 new fields: city, state, residential_status, years_at_address, employer_name, years_in_job
- [ ] Add conditional field logic: employer_name and years_in_job only shown for salaried/business
- [ ] Add a Step 5 "Eligibility Result" screen — after form submit, show pass/fail immediately
      (poll `/api/v1/applications/{id}/status` until lead_capture completes)

### 3.2 StatusTracker Updates

- [ ] Add eligibility banner: if current_stage = lead_capture and status = rejected → show reason card
- [ ] Add "Start Assessment" button if status = pending_review (links to AssessmentChat)
- [ ] Show ART offers in a cards layout when art_negotiation stage is completed
      (read from audit events payload — the 3 offers are in stage_results.art_negotiation)

### 3.3 RMDashboard Updates

- [ ] Add NegotiationPanel component alongside AgentDecisionCard
- [ ] Add "Start Assessment" button per application
- [ ] Show offer selection UI: display Options A/B/C with EMI breakdown before RM approves

### 3.4 New Pages

- [ ] `AssessmentChat.tsx` — multi-turn chat page (see Part 2 Agent C)
- [ ] Route `/assessment/:applicationId` in App.tsx

---

## Part 4 — Infrastructure & Observability

### 4.1 Tracing & Evaluation

Per capstone requirements (see Plan.md Phase 5):

- [ ] Add LangSmith tracing to all 7 agent nodes
  - Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env`
  - Wrap each `client.messages.create` call with LangSmith run context
- [ ] Add per-node evaluation metrics logged to `audit_log`:
  - LLM latency (ms)
  - Token usage (input/output)
  - Decision confidence (from LLM output if available)

### 4.2 Notification Service Wiring

- [ ] Implement `send_eligibility_email` task (Node 1 eligible → email)
- [ ] Implement `send_outreach_email` + `send_outreach_sms` tasks (Outreach Agent)
- [ ] Wire SendGrid + Twilio via env vars (already stubbed in notification-service)

### 4.3 Alembic Migration: Lead Gen Fields

```python
# 0006_add_lead_gen_fields.py
op.add_column('applications', sa.Column('city', sa.String(), nullable=True))
op.add_column('applications', sa.Column('state', sa.String(), nullable=True))
op.add_column('applications', sa.Column('residential_status', sa.String(), nullable=True))
op.add_column('applications', sa.Column('years_at_current_address', sa.Integer(), nullable=True))
op.add_column('applications', sa.Column('employer_name', sa.String(), nullable=True))
op.add_column('applications', sa.Column('years_in_current_job', sa.Integer(), nullable=True))
```

---

## Suggested Implementation Order

| Priority | Item | Estimated Complexity |
|----------|------|---------------------|
| 1 | Min loan ₹10k → ₹1k (one-line fix) | Trivial |
| 2 | Expand form fields + migration 0006 | Low |
| 3 | Node 4 mock CIBIL tool (tool_use) | Medium |
| 4 | Applications Monitoring Agent | Medium |
| 5 | Outreach Agent + notification wiring | Medium |
| 6 | Assessment Agent + chat UI | High |
| 7 | Negotiation Panel in RMDashboard | Medium |
| 8 | LangSmith tracing | Low |
| 9 | Eligibility banner + ART offers UI | Low |

---

## Directory Map for New Files

```
agent-service/
├── agents/
│   ├── monitoring/
│   │   ├── __init__.py
│   │   └── agent.py              ← run_monitoring_scan()
│   ├── outreach/
│   │   ├── __init__.py
│   │   └── agent.py              ← run_outreach(application_id, context)
│   ├── assessment/
│   │   ├── __init__.py
│   │   └── agent.py              ← AssessmentSession class
│   └── negotiation/
│       ├── __init__.py
│       └── agent.py              ← run_negotiation_analysis(state)
├── config/prompts/
│   ├── outreach.j2
│   ├── assessment.j2
│   └── negotiation.j2

backend-api/
├── db/migrations/versions/
│   └── 0006_add_lead_gen_fields.py
├── routers/
│   └── assessment.py             ← chat session endpoints + WS

frontend/src/
├── pages/
│   └── AssessmentChat.tsx
└── components/
    ├── ChatBubble.tsx
    └── NegotiationPanel.tsx
```
