import os
from pydantic import BaseModel
from dotenv import load_dotenv


class Settings(BaseModel):
    env: str = "dev"
    log_level: str = "INFO"
    model_provider: str = "openai"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    vault_addr: str | None = None
    vault_token: str | None = None
    aws_region: str = "us-east-1"
    sqs_queue_url: str | None = None
    twilio_auth_token: str | None = None
    mcp_server_transport: str = "stdio"
    policy_kill_switch: bool = False
    tenant_id: str = "local-tenant"


def _load_settings() -> Settings:
    load_dotenv()
    return Settings(
        env=os.getenv("ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        model_provider=os.getenv("MODEL_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        vault_addr=os.getenv("VAULT_ADDR"),
        vault_token=os.getenv("VAULT_TOKEN"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        sqs_queue_url=os.getenv("SQS_QUEUE_URL"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        mcp_server_transport=os.getenv("MCP_SERVER_TRANSPORT", "stdio"),
        policy_kill_switch=os.getenv("POLICY_KILL_SWITCH", "false").lower() == "true",
        tenant_id=os.getenv("TENANT_ID", "local-tenant"),
    )


settings = _load_settings()
