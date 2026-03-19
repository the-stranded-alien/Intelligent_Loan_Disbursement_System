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

## Summary

| Phase | Status | Priority |
|---|---|---|
| Phase 1 — Agent nodes (6 remaining) | 🔄 Partial | **High** — core product doesn't work without real node decisions |
| Phase 2 — Auth (Auth0) | Not started | **High** — nothing is secured without this |
| Phase 3 — Notifications | Not started | Medium — user-facing feature |
| Phase 4 — Hardening | Not started | Low–Medium — production readiness |
