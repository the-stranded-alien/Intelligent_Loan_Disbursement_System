---
description: Run a single LangGraph agent node in isolation with a mock ApplicationState
argument-hint: "lead_capture | lead_qualification | identity_verification | credit_assessment | fraud_detection | compliance | document_collection | sanction_processing | disbursement"
---

## Context

- Available agents: !`ls agent-service/agents/ 2>/dev/null || echo "agents/ not found"`
- Agent to test: $ARGUMENTS
- Graph state definition: !`cat agent-service/graph/state.py 2>/dev/null || echo "state.py not found"`
- Agent file: !`cat agent-service/agents/$ARGUMENTS/agent.py 2>/dev/null || echo "agent not found"`
- Tools file: !`cat agent-service/agents/$ARGUMENTS/tools.py 2>/dev/null || echo "tools not found"`

## Your task

Test the **$ARGUMENTS** agent node in isolation by invoking it directly with a mock `ApplicationState`.

### Steps

1. **Validate argument** — if `$ARGUMENTS` is empty or not a valid agent name, list the available agents and ask which one to test.

2. **Read the agent and its tools** to understand the current implementation.

3. **Create a test script** at `agent-service/tests/test_agent_<name>.py` (overwrite if exists):
   - Import the agent's `run()` or `invoke()` function
   - Build a realistic mock `ApplicationState` with:
     - `application_id`: a UUID
     - `applicant_name`: "Test User"
     - `pan_number`: "ABCDE1234F"
     - `monthly_income`: 75000
     - `loan_amount`: 500000
     - `loan_purpose`: "home renovation"
     - `phone`: "+919876543210"
     - `email`: "test@example.com"
     - Stage-specific fields as required by this agent
   - Patch / mock all external API calls (CIBIL, OCR, Twilio, etc.) using `unittest.mock`
   - Assert the returned state has the expected output keys set
   - Assert no exceptions are raised

4. **Run the test**:
   ```
   docker compose exec agent-service python -m pytest agent-service/tests/test_agent_$ARGUMENTS.py -v
   ```
   (Fall back to `python -m unittest` if pytest not available.)

5. **Report** the test result — pass/fail, output, and any errors with suggested fixes.

### Notes
- Never call real external APIs (CIBIL, Experian, Google Document AI, Anthropic) without confirmation.
- Use `monkeypatch` or `unittest.mock.patch` for all I/O.
- If the agent file is missing or only a stub, implement a minimal working version before testing.
