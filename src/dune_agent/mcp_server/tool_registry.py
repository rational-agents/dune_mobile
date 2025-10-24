from ..tools.cpaas_sms import send_sms, SmsPayload


def register_tools(app):
    @app.tool()
    def health() -> str:
        return "ok"

    @app.tool()
    def cpaas_sms_send(tenantId: str, userId: str, content: str) -> dict:
        payload = SmsPayload(tenantId=tenantId, userId=userId, content=content)
        return send_sms(payload)
