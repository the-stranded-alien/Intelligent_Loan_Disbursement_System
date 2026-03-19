# Loan Disbursement System — Remaining Plan

## Phase 1 — Complete Agent Nodes (6 stubs remaining)

All nodes must follow the `lead_capture` / `sanction_processing` pattern: render Jinja2 prompt → call Claude → parse JSON → publish `node.completed` → return updated state.

| Node | State fields to set | Router to wire |
|---|---|---|
| `lead_qualification` | `qualification_result: qualified\|rejected`, `qualification_notes` | `route_after_qualification` — currently always returns `"continue"` |
| `identity_verification` | `identity_verified: bool`, `kyc_status`, `identity_provider_response` | none (linear edge) |
| `credit_assessment` | `credit_score`, `credit_decision: approve\|reject\|manual_review`, `suggested_loan_amount` | none (linear edge) |
| `fraud_detection` | `fraud_risk_score`, `fraud_signals`, `fraud_decision: clear\|flag\|block` | `route_after_fraud` — currently always returns `"continue"` |
| `compliance` | `compliance_checks`, `compliance_decision: pass\|fail`, `compliance_notes` | none (linear edge) |
| `document_collection` | `documents_verified: bool`, `required_documents`, `ocr_results` | none (linear edge) |
| `disbursement` | `disbursement_status: success\|failed`, `disbursement_reference` | none; on failure enqueue `retry_disbursement` Celery task |

**Also wire the two stub routers** once the nodes above produce real output fields:
- `route_after_qualification` → `"continue"` if `qualification_result == "qualified"` else `"reject"`
- `route_after_fraud` → `"block"` if `fraud_decision == "block"` else `"continue"`

**Also implement `retry_disbursement`** Celery task (`agent-service/worker/tasks.py`):
- Retry schedule: immediate → 1 h → 4 h → 24 h (max 4 retries, already configured)
- On permanent failure: set `disbursement_status = "failed"`, publish `pipeline.completed`

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
2. `worker/tasks.py` — implement four Celery tasks:
   - `send_stage_notification` — stage update SMS/email to applicant on each `node.completed`
   - `send_rejection_notification` — rejection reason + improvement guidance on `pipeline.completed` with rejected status
   - `send_disbursement_confirmation` — success message + EMI schedule on successful disbursement
   - `send_rm_hitl_alert` — alert RM channel/email when `hitl.requested` fires
3. Wire `twilio_service.py` (SMS/WhatsApp) and `sendgrid_service.py` (email) — both are scaffolded, just need credentials and call sites
4. Deploy `notification-service` + `notification-worker` to Railway
5. Add env vars to Railway: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `SENDGRID_API_KEY`

---

## Phase 4 — Hardening

| Item | File | What to do |
|---|---|---|
| **Celery Beat** | `docker-compose.yml` + `agent-service/worker/` | Deploy `celery-beat` container; add scheduled tasks: doc reminder at 24h/48h/72h, RM follow-up after 5 days stalled, sanction nudge after 48h |
| **Error handling** | `backend-api/services/event_consumer.py` | On node failure (pipeline error), set `Application.status = "error"` and broadcast WebSocket event; show error state in `WorkflowTimeline` |
| **RAG / pgvector** | `agent-service/agents/compliance/agent.py` | Run `/seed-rag` to populate pgvector with RBI guidelines; wire `policy_rag_tool` to query embeddings and inject relevant policy into the compliance prompt |

---

## Phase 5 — Capstone Excellence

Four criteria must all be satisfied for the capstone submission. Each maps to concrete implementation work below.

---

### 5.1 — ≥ 3 Named Agents (Retriever · Analyst · Critic · Planner)

The pipeline already has 9 nodes, but the capstone requires **explicitly named agent roles** that are architecturally visible — not just a chain of identical LLM calls. Map and implement as follows:

| Capstone Role | Node(s) | What it does |
|---|---|---|
| **Retriever** | `compliance` | Queries pgvector (RBI guidelines, AML rules) via `policy_rag_tool` — retrieves relevant policy chunks and injects them into the prompt. This is the canonical Retriever: it fetches external knowledge the other agents need. |
| **Analyst** | `credit_assessment`, `fraud_detection` | Runs structured quantitative analysis: credit scoring model + fraud signal scoring. Both produce numeric outputs (credit_score, fraud_risk_score) that downstream agents consume. |
| **Critic** | `lead_qualification`, `identity_verification` | Reviews the Analyst's inputs and the applicant's submitted data, flags inconsistencies, and decides pass/fail with explicit reasoning (`qualification_notes`, `identity_provider_response`). |
| **Planner** | `sanction_processing` | Synthesises all upstream outputs (credit, fraud, compliance, HITL if present) and produces the final action plan: sanctioned amount, interest rate, tenure, EMI schedule, terms. This is the Planner: it coordinates the pipeline's final decision. |

**Implementation steps:**
1. Add a `AGENT_ROLE` constant to each agent file (`"retriever"`, `"analyst"`, `"critic"`, `"planner"`) — used in trace logging (§5.2).
2. Implement the Retriever role in `compliance/agent.py` (already listed in Phase 4 RAG item — promote it to Phase 5 critical path).
3. Ensure Analyst nodes (`credit_assessment`, `fraud_detection`) produce **quantitative numeric outputs** — not just labels. Credit score must be an integer 300–900; fraud risk score must be a float 0–1.
4. Ensure Critic nodes include an explicit `reasoning` field in their JSON output (e.g., `"qualification_reasoning": "..."`) — required for trace logging.
5. `sanction_processing` prompt must reference all upstream agent outputs by name — demonstrating Planner coordination.

---

### 5.2 — Agent Reasoning Traces

Every LLM call across all 9 nodes must be logged as a structured reasoning trace so the capstone evaluator can inspect what each agent decided and why.

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
4. For the Retriever (`compliance`): also log `rag_chunks_used` — the top-k chunks returned by pgvector with their cosine similarity scores.
5. **New API endpoint** `GET /api/v1/applications/{id}/traces` in `backend-api/routers/applications.py` — returns all `AgentTrace` rows for an application, ordered by `created_at`. Used by the demo dashboard (§5.4).

---

### 5.3 — Quantitative + Qualitative Evaluation

Both types of evaluation must be implemented and surfaced in the demo dashboard.

**Quantitative metrics** (already partially tracked via `/analytics` endpoints — extend them):

| Metric | Source | Endpoint |
|---|---|---|
| Overall approval rate | `applications` table | `/analytics/summary` (existing) |
| Per-stage rejection rate | `audit_log` | `/analytics/agents` (existing) |
| Mean credit score (approved vs rejected) | `agent_traces.parsed_output` | `/analytics/evaluation` (new) |
| Mean fraud risk score (approved vs rejected) | `agent_traces.parsed_output` | `/analytics/evaluation` (new) |
| Mean pipeline duration (lead_capture → disbursement) | `agent_traces.created_at` diff | `/analytics/evaluation` (new) |
| HITL intervention rate (% of apps that needed RM) | `applications` where `hitl_required=true` | `/analytics/evaluation` (new) |
| Disbursement success rate | `applications` where `disbursement_status=success` | `/analytics/evaluation` (new) |
| LLM token usage per node (avg) | `agent_traces` aggregated by node | `/analytics/evaluation` (new) |

**Qualitative metrics** (from `agent_traces`):

| Metric | How to compute |
|---|---|
| Reasoning coherence score | Prompt Claude (offline / batch job) to rate each `raw_llm_response` 1–5 for logical consistency |
| Critic false-positive rate | % of `lead_qualification` rejections that had credit_score > 650 (contradiction flagged) |
| Planner term alignment | Check that `sanction_amount ≤ suggested_loan_amount` — misalignment logged as a quality flag |
| RAG retrieval relevance | For each Retriever call, log similarity scores; alert if top chunk similarity < 0.75 |

**Implementation steps:**
1. Add `GET /api/v1/analytics/evaluation` endpoint returning all quantitative metrics above.
2. Add `GET /api/v1/analytics/quality-flags` endpoint that scans recent traces and returns qualitative flags (contradiction, misalignment, low RAG similarity).
3. Add a `POST /api/v1/analytics/run-coherence-check` endpoint that batches the last N `raw_llm_response` texts to Claude for reasoning quality scoring, stores results back in a `coherence_score` column on `agent_traces`.

---

### 5.4 — Demo Dashboard + Evaluation Report

**Demo dashboard** — new `frontend/src/pages/EvaluationDashboard.tsx` page, accessible at `/eval` (RM only):

| Section | Content |
|---|---|
| **Agent Inventory** | Table listing all 4 named roles, their mapped nodes, call count, avg token usage, avg duration |
| **Quantitative Scorecard** | Grid of metric cards (approval rate, HITL rate, disbursement success, avg credit score, avg fraud score, avg pipeline duration) from `/analytics/evaluation` |
| **Qualitative Flags** | List of recent quality flags from `/analytics/quality-flags` — contradictions, misalignments, low RAG similarity — each linkable to the trace |
| **Reasoning Trace Explorer** | Search by application ID → accordion showing each node's trace: prompt sent, raw LLM response, parsed output, token counts, duration |
| **Per-Node Performance** | Recharts BarChart — avg duration + avg tokens per node |
| **RAG Retrieval Quality** | For compliance node: histogram of top-chunk similarity scores; alert if median < 0.75 |

**Wire into nav:** Add "Eval" nav item (BarChart4 icon) in `App.tsx` — visible to RM role only (guarded after Phase 2 Auth0).

**Evaluation Report** — `EVALUATION.md` at repo root:

Sections to include:
1. **Agent Architecture** — diagram (ASCII or Mermaid) showing the 4 roles and their dependencies in the 9-node graph
2. **Reasoning Trace Sample** — copy 2–3 real trace records (one per role) with prompt excerpt, LLM response excerpt, parsed output
3. **Quantitative Results** — table of all metrics from `/analytics/evaluation` populated with real run data
4. **Qualitative Analysis** — discussion of coherence scores, any contradictions found, RAG retrieval quality
5. **Limitations & Future Work** — what stub nodes don't cover, how the Retriever could be extended

---

## Summary

| Phase | Status | Priority |
|---|---|---|
| Phase 1 — Agent nodes (6 remaining) | 🔄 Partial | **High** — core product doesn't work without real node decisions |
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

Phase 4 RAG item (pgvector + compliance) is a **prerequisite for 5.1** (the Retriever role). Implement it before the rest of Phase 5.
