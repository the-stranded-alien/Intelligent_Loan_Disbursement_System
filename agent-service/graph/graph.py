from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from graph.state import ApplicationState
from graph.router import route_after_qualification, route_after_fraud, route_after_sanction
from agents.lead_capture.agent import run_lead_capture
from agents.lead_qualification.agent import run_lead_qualification
from agents.identity_verification.agent import run_identity_verification
from agents.credit_assessment.agent import run_credit_assessment
from agents.fraud_detection.agent import run_fraud_detection
from agents.compliance.agent import run_compliance
from agents.document_collection.agent import run_document_collection
from agents.sanction_processing.agent import run_sanction_processing
from agents.disbursement.agent import run_disbursement


def build_graph(checkpointer: AsyncPostgresSaver | None = None) -> StateGraph:
    """Build and compile the 9-node LangGraph pipeline."""
    builder = StateGraph(ApplicationState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    builder.add_node("lead_capture", run_lead_capture)
    builder.add_node("lead_qualification", run_lead_qualification)
    builder.add_node("identity_verification", run_identity_verification)
    builder.add_node("credit_assessment", run_credit_assessment)
    builder.add_node("fraud_detection", run_fraud_detection)
    builder.add_node("compliance", run_compliance)
    builder.add_node("document_collection", run_document_collection)
    builder.add_node("sanction_processing", run_sanction_processing)
    builder.add_node("disbursement", run_disbursement)

    # ── Entry point ────────────────────────────────────────────────────────────
    builder.set_entry_point("lead_capture")

    # ── Edges ──────────────────────────────────────────────────────────────────
    builder.add_edge("lead_capture", "lead_qualification")

    builder.add_conditional_edges(
        "lead_qualification",
        route_after_qualification,
        {"continue": "identity_verification", "reject": END},
    )

    builder.add_edge("identity_verification", "credit_assessment")

    builder.add_conditional_edges(
        "fraud_detection",
        route_after_fraud,
        {"continue": "compliance", "block": END},
    )

    builder.add_edge("credit_assessment", "fraud_detection")
    builder.add_edge("compliance", "document_collection")
    builder.add_edge("document_collection", "sanction_processing")

    builder.add_conditional_edges(
        "sanction_processing",
        route_after_sanction,
        {
            "disburse": "disbursement",
            "hitl": "sanction_processing",  # interrupt + resume at same node
            "reject": END,
        },
    )

    builder.add_edge("disbursement", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["sanction_processing"],
    )
