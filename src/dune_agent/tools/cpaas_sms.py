from pydantic import BaseModel, Field
from ..siem import emit_audit_event
from ..config import settings


class SmsPayload(BaseModel):
    tenantId: str = Field(..., description="Tenant identifier")
    userId: str = Field(..., description="User identifier")
    content: str = Field(..., min_length=1, max_length=1000)


def send_sms(payload: SmsPayload) -> dict:
    if settings.policy_kill_switch:
        return {"status": "blocked", "reason": "kill_switch_enabled"}
    emit_audit_event(
        "tool_call.cpaas_sms.send", payload.model_dump(), redactions=["content"]
    )
    # Placeholder for provider API call via short-lived credentials
    return {"status": "queued", "messageId": "demo-123", "provider": "mock"}
