from langgraph.graph import StateGraph, END
from .state import WorkflowState
from ..policies import sanitize_input, policy_check
from ..siem import emit_audit_event


def node_probe(state: WorkflowState) -> WorkflowState:
    text = sanitize_input(state.get("user_input", ""))
    reply = f"[probe] Hi, quick question about your preferences: {text[:64]}"
    ok, _ = policy_check(reply)
    if not ok:
        reply = "[probe] Response blocked by policy"
    emit_audit_event("node_probe", {"reply": reply}, [])
    state["agent_output"] = reply
    state["state"] = "persuade"
    return state


def node_persuade(state: WorkflowState) -> WorkflowState:
    reply = "[persuade] Here is a short approved elaboration."
    ok, _ = policy_check(reply)
    if not ok:
        reply = "[persuade] Response blocked by policy"
    emit_audit_event("node_persuade", {"reply": reply}, [])
    state["agent_output"] = reply
    state["state"] = "decision"
    return state


def node_decision(state: WorkflowState) -> WorkflowState:
    reply = "[decision] Thanks. We'll follow up."
    ok, _ = policy_check(reply)
    if not ok:
        reply = "[decision] Response blocked by policy"
    emit_audit_event("node_decision", {"reply": reply}, [])
    state["agent_output"] = reply
    state["state"] = "done"
    return state


def build_graph():
    g = StateGraph(WorkflowState)
    g.add_node("probe", node_probe)
    g.add_node("persuade", node_persuade)
    g.add_node("decision", node_decision)
    g.set_entry_point("probe")
    g.add_edge("probe", "persuade")
    g.add_edge("persuade", "decision")
    g.add_edge("decision", END)
    return g.compile()
