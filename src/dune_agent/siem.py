from .logging import logger


def emit_audit_event(event_type: str, payload: dict, redactions: list[str] | None = None):
    redactions = redactions or []
    scrubbed = {k: ("[REDACTED]" if k in redactions else v) for k, v in payload.items()}
    logger.info("audit_event", event_type=event_type, **scrubbed)
