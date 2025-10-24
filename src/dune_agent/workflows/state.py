from typing import TypedDict


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    user_input: str
    agent_output: str
    state: str  # "probe" | "persuade" | "decision" | "done"
