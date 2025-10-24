# Dune MCP Agent

Implements a Python MCP agentic system with:
- LangChain agents (foundation for tool-calling)
- LangGraph workflows (finite-state dialogue)
- MCP server tools (FastMCP) exposing allow-listed tools
- Security alignments per `dune-security.md`

## Prerequisites

- Python 3.11+
- macOS environment (as used here)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` as needed.

## Run

- Workflow demo:
```bash
python -m dune_agent.cli run-workflow "Hi there"
```

- MCP server (stdio):
```bash
python -m dune_agent.cli start-mcp
```

This starts an MCP server named `dune-mcp` exposing:
- `health() -> "ok"`
- `cpaas_sms_send(tenantId, userId, content) -> {status, messageId, provider}`

## Security Alignment

- **Isolation**: Workflows scoped by `tenant_id`. Future SQS FIFO adapter uses `{tenantId}:{userId}` `MessageGroupId`.
- **Secrets**: Dev `.env` only. Production uses Vault/KMS via `secrets.py` (stub) with dynamic secrets.
- **Abuse/Audit**: `POLICY_KILL_SWITCH`, `policies.py` gate, and `siem.py` audit events for every tool call.
- **Webhook authenticity**: Placeholder module `tools/cpaas_sms.py`; add signature checks per provider in webhooks module.
- **LLM safety**: Hardened prompt in `agents/system_prompt.py`. Workflows enforce finite states.

## Testing

```bash
pytest -q
```

## Deployment

- Use a Python 3.11 container base.
- Provide environment via secret manager.
- Pin IAM to least-privilege for SQS/KMS where applicable.
- Expose MCP via stdio for IDE/agent runtimes; consider TCP transport for remote orchestration.

## Notes

- `dune_architecture.md` currently has minimal content; update to reflect any additional constraints.
- See `dune-security.md` for detailed controls.
