---
description: Add a new agent node to the LangGraph pipeline (agent.py, tools.py, prompt, graph wiring, state fields)
argument-hint: "<agent_name> — e.g. risk_scoring"
---

## Context

- Existing agents: !`ls agent-service/agents/ 2>/dev/null || echo "agents/ not found"`
- Graph file: !`cat agent-service/graph/graph.py 2>/dev/null || echo "graph.py not found"`
- State definition: !`cat agent-service/graph/state.py 2>/dev/null || echo "state.py not found"`
- Router: !`cat agent-service/graph/router.py 2>/dev/null || echo "router.py not found"`
- Existing prompts: !`ls agent-service/config/prompts/ 2>/dev/null`

## Your task

Add a new agent node called **$ARGUMENTS** to the LangGraph pipeline.

If `$ARGUMENTS` is empty, ask the user for the agent name and its purpose before proceeding.

### Steps

1. **Clarify with the user**:
   - What does this agent do?
   - Where should it sit in the pipeline (after which node, before which node)?
   - What inputs does it need from `ApplicationState`?
   - What outputs does it write back to state?
   - Does it require HITL? (interrupt before or after?)
   - What external APIs or tools does it call?

2. **Create `agent-service/agents/$ARGUMENTS/`**:

   `agent.py` — Full implementation stub:
   ```python
   from agent_service.graph.state import ApplicationState
   from agent_service.agents.$ARGUMENTS.tools import <relevant_tools>
   from langchain_anthropic import ChatAnthropic
   from langchain_core.messages import SystemMessage, HumanMessage
   from jinja2 import Environment, FileSystemLoader

   llm = ChatAnthropic(model="claude-sonnet-4-6").bind_tools([...])

   async def run_$ARGUMENTS(state: ApplicationState) -> ApplicationState:
       # Load prompt, call LLM, parse response, update state
       ...
   ```

   `tools.py` — Tool stubs with docstrings describing what each tool does.

3. **Create `agent-service/config/prompts/$ARGUMENTS.j2`**:
   - System prompt explaining the agent's role
   - Input variables section ({{ applicant_name }}, {{ loan_amount }}, etc.)
   - Output format specification (JSON schema)
   - Decision criteria

4. **Update `agent-service/graph/state.py`**:
   - Add any new fields required by this agent to `ApplicationState`
   - Add a `<agent_name>_result: Optional[dict]` field
   - Add a `<agent_name>_status: Optional[str]` field

5. **Update `agent-service/graph/graph.py`**:
   - Import the new agent function
   - Add `graph.add_node("<agent_name>", run_$ARGUMENTS)`
   - Wire edges: remove the old direct edge between predecessor and successor, add edges through this new node
   - Add conditional edges if needed

6. **Update `agent-service/graph/router.py`**:
   - Add routing logic for the new node if it has conditional branches

7. **Generate an Alembic migration** if new DB columns are needed:
   - Instruct the user to run `/migrate new "add <agent_name> fields"`

8. **Write a test** using the same pattern as `/test-agent` for this new agent.

9. **Show a diff summary** of all files changed/created.
