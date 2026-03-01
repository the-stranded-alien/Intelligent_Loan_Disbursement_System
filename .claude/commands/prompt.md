---
description: View, edit, or iterate on a Jinja2 prompt template for an agent node
argument-hint: "lead_qualification | identity_verification | credit_assessment | fraud_detection | compliance | document_collection | sanction_processing | disbursement"
---

## Context

- Available prompts: !`ls agent-service/config/prompts/ 2>/dev/null || echo "prompts/ not found"`
- Target prompt: !`cat agent-service/config/prompts/$ARGUMENTS.j2 2>/dev/null || echo "Prompt not found — will create"`
- Agent implementation: !`cat agent-service/agents/$ARGUMENTS/agent.py 2>/dev/null | head -40 || echo ""`
- State fields used: !`grep -n "$ARGUMENTS" agent-service/graph/state.py 2>/dev/null | head -20 || echo ""`

## Your task

Work on the Jinja2 prompt template for the **$ARGUMENTS** agent node.

If `$ARGUMENTS` is empty, list all available prompts and ask which one to work on.

### Default flow (view + improve)

1. **Read the current prompt** (shown in context above).

2. **Read the agent implementation** to understand what variables are injected and what output format is expected.

3. **Analyze the prompt quality** against these criteria:
   - Clear system role definition
   - All required state variables referenced (e.g. `{{ applicant_name }}`, `{{ loan_amount }}`)
   - Explicit output format (JSON schema with field names and types)
   - Decision criteria clearly stated
   - Edge cases handled (missing data, boundary values)
   - Appropriate length — not too long (LLM costs), not too vague

4. **Suggest specific improvements** — show a diff of proposed changes.

5. **Ask the user** if they want to:
   a. Apply the suggested improvements
   b. Rewrite the prompt from scratch
   c. Just view the current prompt without changes
   d. Test the prompt with a sample payload

### If option (d) — test the prompt

Render the template with realistic sample data and show what the LLM would receive:
```python
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("agent-service/config/prompts"))
template = env.get_template("$ARGUMENTS.j2")
rendered = template.render(
    applicant_name="Priya Sharma",
    pan_number="BCDFE4321G",
    loan_amount=750000,
    monthly_income=90000,
    ...
)
print(rendered)
```

Show the rendered prompt and estimate token count.

### Rules
- Never make the prompt longer without good reason — token efficiency matters.
- Always keep the output format as a strict JSON schema — the agent parser depends on it.
- Variable names must match exactly what's in `ApplicationState`.
