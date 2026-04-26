from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from graph.state import ApplicationState
from graph.router import (
    route_after_lead_capture,
    route_after_qualification,
    route_after_identity,
    route_after_credit,
    route_after_art,
)
from agents.lead_capture.agent import run_lead_capture
from agents.lead_qualification.agent import run_lead_qualification
from agents.identity_verification.agent import run_identity_verification
from agents.credit_assessment.agent import run_credit_assessment
from agents.art_negotiation.agent import run_art_negotiation
from agents.enach.agent import run_enach
from agents.esign.agent import run_esign


def build_graph(checkpointer: AsyncPostgresSaver | None = None) -> StateGraph:
    """Build and compile the 7-node LangGraph pipeline.

    Pipeline:
      lead_capture
        ↓ eligible / ineligible → END
      lead_qualification
        ↓ pass / fail → END
      identity_verification
        ↓ verified / failed → END
      credit_assessment
        ↓ approve / reject → END
      art_negotiation          ← interrupt_before here (HITL for loans > ₹2L)
        ↓ continue / reject → END
      enach
        ↓
      esign
        ↓ END
    """
    builder = StateGraph(ApplicationState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    builder.add_node("lead_capture",          run_lead_capture)
    builder.add_node("lead_qualification",    run_lead_qualification)
    builder.add_node("identity_verification", run_identity_verification)
    builder.add_node("credit_assessment",     run_credit_assessment)
    builder.add_node("art_negotiation",       run_art_negotiation)
    builder.add_node("enach",                 run_enach)
    builder.add_node("esign",                 run_esign)

    # ── Entry point ────────────────────────────────────────────────────────────
    builder.set_entry_point("lead_capture")

    # ── Edges ──────────────────────────────────────────────────────────────────
    builder.add_conditional_edges(
        "lead_capture",
        route_after_lead_capture,
        {"qualify": "lead_qualification", "reject": END},
    )

    builder.add_conditional_edges(
        "lead_qualification",
        route_after_qualification,
        {"continue": "identity_verification", "reject": END},
    )

    builder.add_conditional_edges(
        "identity_verification",
        route_after_identity,
        {"continue": "credit_assessment", "reject": END},
    )

    builder.add_conditional_edges(
        "credit_assessment",
        route_after_credit,
        {"continue": "art_negotiation", "reject": END},
    )

    builder.add_conditional_edges(
        "art_negotiation",
        route_after_art,
        {
            "continue": "enach",
            "hitl":    "art_negotiation",  # interrupt + resume at same node
            "reject":  END,
        },
    )

    builder.add_edge("enach", "esign")
    builder.add_edge("esign", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["identity_verification", "art_negotiation"],
    )
