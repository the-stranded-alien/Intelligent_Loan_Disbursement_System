# Loan Disbursement System — Remaining Plan

## Phase 1 — Complete Agent Nodes (revised pipeline)

All nodes follow the same pattern: render Jinja2 prompt → call Claude → parse JSON → publish `node.completed` → return updated state.

### Revised 7-Node Pipeline

```
lead_gen → lead_qualification → identity_verification → credit_assessment
         → art_negotiation → e_nach → e_sign
```

HITL threshold: ₹1,00,000 (₹1L)

---

#### Node 1 — `lead_gen` (Lead Generation)

| | |
|---|---|
| **Inputs** | Web form fields: full name, mobile, email, date of birth, PAN number, employment type, monthly income, loan amount requested, loan purpose, city, pincode |
| **Outputs** | `lead_valid: bool`, `lead_rejection_reason` (if invalid) |
| **Logic** | Validates form completeness and basic field rules only — no document check. No LLM call needed; pure validation logic. |
| **Pass/Fail** | Fail → immediate rejection page. Pass → eligible confirmation + trigger email: "You are eligible, please complete your KYC." |
| **Router** | `route_after_lead_gen` → `"continue"` if `lead_valid == true` else `"reject"` |

**Email on pass:** "Congratulations, you are eligible! Please complete your KYC to proceed." (notification-service, Phase 3)

---

#### Node 2 — `lead_qualification` (Document Qualification)

| | |
|---|---|
| **Inputs** | Salary slips (last 3 months), ITR returns (last 2 years), loan amount requested |
| **Outputs** | `qualification_result: pass\|fail\|manual_review`, `qualification_notes`, `validated_income`, `validated_loan_eligibility` |
| **Logic** | LLM validates document authenticity signals, cross-checks stated income vs salary slips vs ITR. Determines if documents support requested loan amount. |
| **Pass/Fail/Not Sure** | `pass` → proceed to KYC. `fail` → reject with reason. `manual_review` → ask applicant to re-upload / verify documents. |
| **Router** | `route_after_qualification` → `"continue"` / `"manual_review"` / `"reject"` |

---

#### Node 3 — `identity_verification` (KYC)

| | |
|---|---|
| **Inputs** | PAN card image, selfie/photo |
| **Outputs** | `identity_verified: bool`, `pan_match: bool`, `kyc_status: verified\|failed`, `identity_provider_response` |
| **Logic** | LLM (mocked: Google Doc AI in prod) checks PAN number extracted from image matches declared PAN. Facial match signal. |
| **Pass/Fail** | `pan_match == false` or `identity_verified == false` → reject. Pass → proceed to credit assessment. |
| **Router** | None (linear edge, but node sets `identity_verified` — graph can conditionally branch on failure) |

---

#### Node 4 — `credit_assessment`

| | |
|---|---|
| **Inputs** | PAN number, bank statement details, salary slips, `validated_income` from Node 2 |
| **Outputs** | `credit_score: int (300–900)`, `credit_decision: approve\|reject`, `credit_notes` |
| **Logic** | LLM mocks CIBIL API call using PAN + income signals. Produces numeric credit score. Approve if score ≥ threshold. |
| **Pass/Fail** | `reject` → pipeline ends with rejection. `approve` → proceed to ART. |
| **Router** | `route_after_credit` → `"continue"` if `credit_decision == "approve"` else `"reject"` |

---

#### Node 5 — `art_negotiation` (Amount · Rate · Tenure + Negotiation)

Two sub-agents in one node:

**ART Agent** — proposes initial terms based on credit score + income:
- `sanctioned_amount` (≤ requested, adjusted for risk)
- `interest_rate` (%, based on credit score band)
- `tenure_months`
- `emi_amount`

**Negotiation Agent** — HITL for loans ≤ ₹1L (auto-approve); for edge cases, presents counter-offer to applicant:
- If `credit_score` is borderline, reduce amount or increase rate and re-offer
- Applicant can accept or counter (up to 2 rounds)
- Final terms locked: `final_amount`, `final_rate`, `final_tenure`, `final_emi`

| | |
|---|---|
| **Inputs** | `credit_score`, `validated_income`, `loan_amount_requested`, `loan_purpose` |
| **Outputs** | `sanctioned_amount`, `interest_rate`, `tenure_months`, `emi_amount`, `negotiation_rounds`, `art_decision: approved\|rejected` |
| **Router** | `route_after_art` → `"continue"` if `art_decision == "approved"` else `"reject"` |

Example terms:
- Shikha: ₹1,00,000 @ 12% for 2 years
- Sahil: ₹1,00,000 @ 15% for 3 years
- Mou: ₹1,00,000 @ 14% for 3 years

---

#### Node 6 — `e_nach` (Electronic NACH / Auto-Debit Mandate)

| | |
|---|---|
| **Inputs** | `final_amount`, `final_emi`, `final_tenure`, bank account details |
| **Outputs** | `nach_mandate_id`, `nach_status: registered\|failed`, `nach_bank_reference` |
| **Logic** | Initiates e-NACH mandate registration via payment provider (mocked). Applicant authorises auto-debit for EMI collection. |
| **Pass/Fail** | `failed` → retry once; on permanent failure, notify applicant to retry bank auth. |
| **Router** | None (linear; failure sets status and halts) |

---

#### Node 7 — `e_sign` (Electronic Signature)

| | |
|---|---|
| **Inputs** | Sanction letter (generated from ART terms), `nach_mandate_id` |
| **Outputs** | `esign_reference`, `esign_status: signed\|failed`, `disbursement_triggered: bool` |
| **Logic** | Sends loan agreement to applicant for e-signature (Aadhaar OTP or DSC, mocked). On success, triggers disbursement. |
| **Pass/Fail** | Signed → trigger `disburse_loan` Celery task (immediate → 1h → 4h → 24h retry). Failed → notify applicant. |
| **Router** | `route_after_esign` → `"disburse"` if signed else `"retry_esign"` |

**`disburse_loan` Celery task** (`agent-service/worker/tasks.py`):
- Retry schedule: immediate → 1h → 4h → 24h (max 4 retries)
- On permanent failure: set `disbursement_status = "failed"`, publish `pipeline.completed`
- On success: set `disbursement_status = "success"`, `disbursement_reference`, publish `pipeline.completed`

---

### Supporting Agents (Background / Async)

These run outside the main pipeline graph, triggered by scheduler or events:

#### Applications Monitoring Agent

Runs on a Celery Beat schedule (every X hours). Scans `applications` table for records with no state update in the last N hours/days. Classifies stalled applications by stage and hands them off to the Outreach Agent.

| | |
|---|---|
| **File** | `agent-service/agents/monitoring/agent.py` |
| **Schedule** | Every 4 hours (Celery Beat) |
| **Outputs** | List of stalled `application_id`s + stage + days stalled → enqueues `outreach_task` |

#### Outreach Agent

Triggered per stalled application. Reads applicant details + current application state, generates a personalised follow-up message (email / SMS / WhatsApp), and sends it via notification-service. Tracks response:
- If applicant responds within limit → takes action automatically
- If response requires human decision → escalates to RM
- If no response → schedules up to 3 more follow-ups over 7 days (days 1, 3, 7)

| | |
|---|---|
| **File** | `agent-service/agents/outreach/agent.py` |
| **Channels** | Email (SendGrid), SMS/WhatsApp (Twilio) |
| **Max follow-ups** | 4 total (initial + 3 retries) |
| **State fields** | `outreach_attempts`, `last_outreach_at`, `outreach_status: pending\|responded\|escalated\|exhausted` |

#### Assessment Agent

Conversational agent that chats with the applicant (via a chat interface or WhatsApp) to assess repayment intent and capacity. Triggered when credit score is borderline or documents are ambiguous.

| | |
|---|---|
| **File** | `agent-service/agents/assessment/agent.py` |
| **Mode** | Multi-turn conversation (LangGraph with memory) |
| **Outputs** | `assessment_score: 1–10`, `assessment_summary`, `assessment_decision: proceed\|reject\|escalate` |

#### Negotiation Agent

Standalone agent (also embedded in Node 5 ART). Handles counter-offers when initial ART terms are declined. Manages up to 2 negotiation rounds. References CIBIL signal (via PAN → mocked API) to decide how much flexibility to offer.

| | |
|---|---|
| **File** | `agent-service/agents/negotiation/agent.py` |
| **Inputs** | Initial ART terms, applicant counter-offer, `credit_score` |
| **Outputs** | `counter_offer`, `negotiation_outcome: accepted\|rejected\|best_offer_given` |

---

## Phase 2 — Authentication (Auth0)

Secure all user-facing and RM-facing surfaces with Auth0. Two distinct roles: **Applicant** (self-service) and **RM** (internal reviewer).

### Backend — `backend-api`

1. **Install dependencies** — `python-jose[cryptography]`, `httpx` (for Auth0 JWKS fetch)

2. **`backend-api/middleware/auth.py`** — replace the existing stub with a real JWT verifier:
   - Fetch Auth0 JWKS from `https://{AUTH0_DOMAIN}/.well-known/jwks.json` (cache with TTL)
   - Validate `Authorization: Bearer <token>` on every protected request
   - Decode JWT, verify `aud` (API identifier) and `iss` (Auth0 domain)
   - Extract `sub` (user ID) and `permissions` / `roles` claims into `request.state.user`

3. **Role-based guards** — two FastAPI dependencies:
   - `require_applicant` — any valid Auth0 JWT
   - `require_rm` — JWT must have `role: rm` in the custom claim (`https://loanflow/roles`)

4. **Apply guards to routes:**
   | Router | Guard |
   |---|---|
   | `POST /applications/` | `require_applicant` |
   | `GET /applications/` | `require_rm` |
   | `GET /applications/{id}` | `require_applicant` (own app only) or `require_rm` |
   | `GET /applications/{id}/status` | `require_applicant` |
   | `GET /applications/{id}/events` | `require_applicant` |
   | All `/rm/*` routes | `require_rm` |
   | All `/analytics/*` routes | `require_rm` |

5. **Auth0 Machine-to-Machine token** for `agent-service` → `backend-api` internal calls (if any direct HTTP calls are added later)

6. **Env vars to add:** `AUTH0_DOMAIN`, `AUTH0_API_AUDIENCE`

### Frontend — React SPA

1. **Install** `@auth0/auth0-react`

2. **`frontend/src/main.tsx`** — wrap `<App />` with `<Auth0Provider>`:
   ```
   domain={AUTH0_DOMAIN}
   clientId={AUTH0_CLIENT_ID}
   authorizationParams={{ redirect_uri: window.location.origin, audience: AUTH0_API_AUDIENCE }}
   ```

3. **`frontend/src/hooks/useAuth.ts`** — thin wrapper around `useAuth0` that:
   - Returns `{ user, isRM, token, login, logout, isLoading }`
   - `isRM` = `user['https://loanflow/roles']?.includes('rm')`
   - Attaches `Authorization: Bearer <token>` to all `fetch` calls via an `apiFetch` helper

4. **Route protection:**
   - Unauthenticated users → redirect to Auth0 login
   - `/rm` and `/analytics` → guard with `isRM`; show 403 card if signed in but not RM
   - `/`, `/status`, `/applications` (own) → any authenticated user

5. **Nav bar** — show avatar + logout button when logged in; show `Login` button when not

6. **Auth0 setup (dashboard):**
   - Create a Single Page Application (SPA) — for the React frontend
   - Create an API — `https://api.loanflow.io` (or Railway URL) as the audience identifier
   - Create two Roles: `rm`, `applicant`
   - Add a post-login Action that injects roles into `https://loanflow/roles` custom claim
   - Allowed Callback / Logout / Web Origins → Railway frontend URL + `localhost:3000`

7. **Env vars to add:** `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`

---

## Phase 3 — Notification Service

Scaffolded but entirely unwired. All work is in `notification-service/`.

1. `consumers/event_consumer.py` — consume `loan:events` stream (group: `notification-service-group`)
2. `worker/tasks.py` — implement Celery tasks:
   - `send_eligibility_notification` — on `lead_gen.passed`: "You are eligible, please complete your KYC"
   - `send_stage_notification` — stage update SMS/email to applicant on each `node.completed`
   - `send_rejection_notification` — rejection reason + improvement guidance on `pipeline.completed` with rejected status
   - `send_disbursement_confirmation` — success message + EMI schedule on successful disbursement
   - `send_rm_hitl_alert` — alert RM channel/email when `hitl.requested` fires
   - `send_outreach_message` — personalised follow-up from Outreach Agent (SMS/WhatsApp/email)
3. Wire `twilio_service.py` (SMS/WhatsApp) and `sendgrid_service.py` (email) — both are scaffolded, just need credentials and call sites
4. Deploy `notification-service` + `notification-worker` to Railway
5. Add env vars to Railway: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `SENDGRID_API_KEY`

---

## Phase 4 — Hardening

| Item | File | What to do |
|---|---|---|
| **Celery Beat** | `docker-compose.yml` + `agent-service/worker/` | Deploy `celery-beat` container; add scheduled tasks: monitoring agent every 4h, doc reminder at 24h/48h/72h, RM follow-up after 5 days stalled, ART nudge after 48h |
| **Error handling** | `backend-api/services/event_consumer.py` | On node failure (pipeline error), set `Application.status = "error"` and broadcast WebSocket event; show error state in `WorkflowTimeline` |
| **RAG / pgvector** | `agent-service/agents/compliance/agent.py` | Run `/seed-rag` to populate pgvector with RBI guidelines; wire `policy_rag_tool` to query embeddings and inject relevant policy into the compliance prompt (used in ART/Negotiation node) |

---

## Phase 5 — Capstone Excellence

Four criteria must all be satisfied for the capstone submission. Each maps to concrete implementation work below.

---

### 5.1 — ≥ 3 Named Agents (Retriever · Analyst · Critic · Planner)

The pipeline has 7 core nodes + 4 supporting agents. Map capstone roles as follows:

| Capstone Role | Node(s) | What it does |
|---|---|---|
| **Retriever** | ART node (policy lookup) | Queries pgvector (RBI guidelines, lending policy) via `policy_rag_tool` — retrieves relevant policy chunks and injects them into the ART prompt. |
| **Analyst** | `credit_assessment`, Assessment Agent | Runs structured quantitative analysis: credit scoring model + repayment capacity assessment. Produces numeric outputs (`credit_score`, `assessment_score`) that downstream agents consume. |
| **Critic** | `lead_qualification`, `identity_verification` | Reviews documents and KYC data, flags inconsistencies, decides pass/fail/manual_review with explicit reasoning. |
| **Planner** | `art_negotiation` (ART sub-agent) | Synthesises all upstream outputs (credit, income, KYC) and produces the final action plan: sanctioned amount, interest rate, tenure, EMI. Coordinates negotiation rounds. |

**Implementation steps:**
1. Add a `AGENT_ROLE` constant to each agent file (`"retriever"`, `"analyst"`, `"critic"`, `"planner"`) — used in trace logging (§5.2).
2. Implement the Retriever role in `art_negotiation/agent.py` — query pgvector for applicable RBI/NBFC lending rate guidelines before computing ART terms.
3. Ensure Analyst nodes produce **quantitative numeric outputs** — credit score must be an integer 300–900; assessment score must be 1–10.
4. Ensure Critic nodes include an explicit `reasoning` field in their JSON output — required for trace logging.
5. `art_negotiation` prompt must reference all upstream agent outputs by name — demonstrating Planner coordination.

---

### 5.2 — Agent Reasoning Traces

Every LLM call across all nodes must be logged as a structured reasoning trace.

**Schema — `AgentTrace` (new DB table):**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `application_id` | UUID FK → `applications` | |
| `agent_role` | varchar | `retriever` / `analyst` / `critic` / `planner` / `coordinator` |
| `node_name` | varchar | e.g. `credit_assessment` |
| `prompt_rendered` | text | Full Jinja2-rendered prompt sent to Claude |
| `raw_llm_response` | text | Full text response from Claude before parsing |
| `parsed_output` | jsonb | The structured JSON the node extracted |
| `rag_chunks_used` | jsonb | For Retriever: which policy chunks were retrieved and their similarity scores |
| `duration_ms` | integer | Wall-clock time for the Claude API call |
| `model` | varchar | `claude-sonnet-4-6` |
| `input_tokens` | integer | From Claude response usage |
| `output_tokens` | integer | From Claude response usage |
| `created_at` | timestamptz | |

**Implementation steps:**
1. Create Alembic migration for `agent_traces` table.
2. Add `trace_logger.py` to `agent-service/services/` — a thin async helper that writes an `AgentTrace` row after every successful or failed LLM call.
3. Call `await trace_logger.log(...)` in every agent node, passing the rendered prompt, raw response, parsed output, and token counts from `response.usage`.
4. For the Retriever (`art_negotiation`): also log `rag_chunks_used` — the top-k chunks returned by pgvector with their cosine similarity scores.
5. **New API endpoint** `GET /api/v1/applications/{id}/traces` in `backend-api/routers/applications.py` — returns all `AgentTrace` rows for an application, ordered by `created_at`.

---

### 5.3 — Quantitative + Qualitative Evaluation

**Quantitative metrics:**

| Metric | Source | Endpoint |
|---|---|---|
| Overall approval rate | `applications` table | `/analytics/summary` (existing) |
| Per-stage rejection rate | `audit_log` | `/analytics/agents` (existing) |
| Mean credit score (approved vs rejected) | `agent_traces.parsed_output` | `/analytics/evaluation` (new) |
| Mean assessment score (approved vs rejected) | `agent_traces.parsed_output` | `/analytics/evaluation` (new) |
| Mean pipeline duration (lead_gen → e_sign) | `agent_traces.created_at` diff | `/analytics/evaluation` (new) |
| HITL intervention rate | `applications` where `hitl_required=true` | `/analytics/evaluation` (new) |
| Disbursement success rate | Celery task outcomes | `/analytics/evaluation` (new) |
| LLM token usage per node (avg) | `agent_traces` aggregated by node | `/analytics/evaluation` (new) |
| Outreach response rate | `outreach_status` field | `/analytics/evaluation` (new) |
| Negotiation acceptance rate | `negotiation_outcome` field | `/analytics/evaluation` (new) |

**Qualitative metrics:**

| Metric | How to compute |
|---|---|
| Reasoning coherence score | Prompt Claude (offline / batch job) to rate each `raw_llm_response` 1–5 for logical consistency |
| Critic false-positive rate | % of `lead_qualification` rejections that had credit_score > 650 (contradiction flagged) |
| Planner term alignment | Check that `sanctioned_amount ≤ requested_amount` — misalignment logged as quality flag |
| RAG retrieval relevance | For each Retriever call, log similarity scores; alert if top chunk similarity < 0.75 |
| Negotiation fairness | Check that counter-offers stay within RBI rate band guidelines |

**Implementation steps:**
1. Add `GET /api/v1/analytics/evaluation` endpoint returning all quantitative metrics above.
2. Add `GET /api/v1/analytics/quality-flags` endpoint that scans recent traces and returns qualitative flags.
3. Add a `POST /api/v1/analytics/run-coherence-check` endpoint that batches the last N `raw_llm_response` texts to Claude for reasoning quality scoring, stores results back in a `coherence_score` column on `agent_traces`.

---

### 5.4 — Demo Dashboard + Evaluation Report

**Demo dashboard** — new `frontend/src/pages/EvaluationDashboard.tsx` page, accessible at `/eval` (RM only):

| Section | Content |
|---|---|
| **Agent Inventory** | Table listing all 4 named roles, their mapped nodes, call count, avg token usage, avg duration |
| **Quantitative Scorecard** | Grid of metric cards (approval rate, HITL rate, disbursement success, avg credit score, avg assessment score, avg pipeline duration, negotiation acceptance rate) |
| **Qualitative Flags** | List of recent quality flags — contradictions, misalignments, low RAG similarity, unfair negotiation offers |
| **Reasoning Trace Explorer** | Search by application ID → accordion showing each node's trace: prompt sent, raw LLM response, parsed output, token counts, duration |
| **Per-Node Performance** | Recharts BarChart — avg duration + avg tokens per node |
| **RAG Retrieval Quality** | For ART node: histogram of top-chunk similarity scores; alert if median < 0.75 |
| **Outreach Funnel** | Stalled → outreach sent → responded → converted — funnel chart |

**Wire into nav:** Add "Eval" nav item (BarChart4 icon) in `App.tsx` — visible to RM role only (guarded after Phase 2 Auth0).

**Evaluation Report** — `EVALUATION.md` at repo root:

1. **Agent Architecture** — diagram (ASCII or Mermaid) showing the 4 roles and their dependencies in the 7-node graph + supporting agents
2. **Reasoning Trace Sample** — copy 2–3 real trace records (one per role) with prompt excerpt, LLM response excerpt, parsed output
3. **Quantitative Results** — table of all metrics from `/analytics/evaluation` populated with real run data
4. **Qualitative Analysis** — discussion of coherence scores, any contradictions found, RAG retrieval quality, negotiation fairness
5. **Limitations & Future Work** — what mock nodes don't cover, how the Outreach/Assessment agents could be extended

---

## Summary

| Phase | Status | Priority |
|---|---|---|
| Phase 1 — Agent nodes (7-node revised pipeline + 4 supporting agents) | Not started | **High** — core product doesn't work without real node decisions |
| Phase 2 — Auth (Auth0) | Not started | **High** — nothing is secured without this |
| Phase 3 — Notifications | Not started | Medium — user-facing feature |
| Phase 4 — Hardening | Not started | Low–Medium — production readiness |
| Phase 5 — Capstone Excellence | Not started | **High** — required for evaluation |

### Phase 5 dependency order

```
5.1 Agent roles defined
  └─► 5.2 Trace logging (needs AGENT_ROLE constants + AgentTrace table)
        └─► 5.3 Evaluation endpoints (query agent_traces)
              └─► 5.4 Demo dashboard + EVALUATION.md (consumes all above)
```

Phase 4 RAG item (pgvector + ART/Negotiation node) is a **prerequisite for 5.1** (the Retriever role). Implement it before the rest of Phase 5.

### Pipeline node → supporting agent dependency

```
lead_gen → lead_qualification → identity_verification → credit_assessment
  └─► Monitoring Agent (polls stalled apps)
        └─► Outreach Agent (personalised follow-up, up to 4 attempts over 7 days)
  credit_assessment (borderline) → Assessment Agent (conversational repayment check)
  art_negotiation ←→ Negotiation Agent (counter-offer rounds, max 2)
```
