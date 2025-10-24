dune_architecture.md

# Dune Security — Pen-Testing Orchestration Architecture (Markdown Spec)

> Acronyms expanded on first use: **Model Context Protocol (MCP)**, **Large Language Model (LLM)**, **Virtual Private Cloud (VPC)**, **Amazon Simple Queue Service (SQS)**, **Amazon Relational Database Service (RDS)**, **Personally Identifiable Information (PII)**, **Communications Platform as a Service (CPaaS)**, **Network as a Service (NaaS)**, **Embedded Universal Integrated Circuit Card (eUICC)**, **Remote SIM Provisioning (RSP)**, **Security Information and Event Management (SIEM)**.

---

## 0) Purpose

Design a scalable, compliant platform to run **opt-in social-engineering penetration tests** (SMS, voice, WhatsApp, Viber, and future channels) against employee targets, capture outcomes, and trigger **just-in-time training**. The system must:

* Initiate tests by **human-in-the-loop** or **schedule**.
* Reach **500+ concurrent users** and scale horizontally.
* Maintain **strong tenant isolation** (per-customer data and infra controls).
* Support **agentic** message/call flows via **MCP** tools with **LangGraph** (workflows) and **LangChain** (agents).

---

## 1) High-Level Diagram

```
+------------------+         +---------------------+       +-------------------------+
| Control Plane    |  Start  | Event Bus / Triggers|       |  Observability          |
| (Ops UI / API)   +-------->+ (cron, buttons)     +------>+  (logs, metrics, SIEM) |
+--------+---------+         +-----------+---------+       +-----------+-------------+
         |                                 |                           ^
         v                                 v                           |
+--------+--------------------+   +--------+---------------------+     |
| LangGraph Orchestrator      |   |  SQS FIFO Queues            |     |
| (Workflows, state, retries) |   |  (per-tenant per-user flow) |     |
+----+---------------+--------+   +-----+-----------------------+     |
     |               |                  |                             |
     |               |                  |                             |
     v               v                  v                             |
+----+----+   +------+-----+    +-------+------+                      |
| Agents |   | MCP Tools  |    | Channel Workers|                     |
|(LangChain)| (standard    |    | (stateless)   |                     |
+----+----+   | interfaces)|    +---+-----------+                     |
     |        +------+-----+        |                                   |
     |               |              |                                   |
     |        +------+----+   +-----+-----+    +-------------------+    |
     |        | Database  |   | CPaaS APIs |    | Device Fleet (opt)|    |
     |        | Tool      |   | (SMS/Voice|    | Android + eUICC   |    |
     |        +------+----+   | /Viber)   |    | RSP-managed       |    |
     |               |        +-----------+    +-------------------+    |
     |               v
     |      +--------+-------------------------------+
     |      | Per-Tenant Data Plane in AWS VPC       |
     |      |   - RDS PostgreSQL (one per customer)  |
     |      |   - Secrets, KMS, SGs, ACLs            |
     |      +----------------------------------------+
```

---

## 2) AWS Foundations

* **Amazon VPC (Virtual Private Cloud)**: Private subnets for app/services and databases; public subnets only for load balancers or egress if required.
* **Compute**: Containers via **Amazon Elastic Container Service (ECS)** on **AWS Fargate** (simpler ops) or **Amazon Elastic Kubernetes Service (EKS)** (max control).
* **Queues**: **Amazon SQS** **First-In-First-Out (FIFO)** with `MessageGroupId = {tenantId}:{userId}` to guarantee per-user ordering & idempotency.
* **Datastores**: **Amazon RDS for PostgreSQL** — **one RDS instance per customer** (true isolation). Small instance types allowed; scale per tenant.
* **Secrets**: **AWS Secrets Manager** for CPaaS keys, database creds, and device-fleet credentials.
* **Encryption**: **AWS Key Management Service (KMS)** for at-rest encryption of RDS, SQS DLQs, and S3 artifacts.
* **Networking/Security**: Security Groups (east-west minimal), Network ACLs, private endpoints for RDS/Secrets, NAT for controlled egress.

---

## 3) Tenant Isolation (Data Plane)

**Hard isolation**: Each customer receives a **dedicated RDS PostgreSQL instance** (own subnet group, own KMS key if desired). **No cross-tenant joins** possible.

**Database Tool (MCP-exposed)**:

* Maintains a secure routing map: `{tenantId -> RDS endpoint, credentials, KMS key}`.
* Exposes read/write primitives to agents (e.g., `targets.list`, `results.write`, `consent.verify`), **without** leaking connection details to agents.
* Enforces **access control** and **row-level constraints** on every call.
* Rotates credentials via Secrets Manager; supports **Just-In-Time** creds if using IAM auth.

**Stored data per tenant**:

* **PII**: employee identity, contact info (phone, messaging IDs), locale, timezone.
* **Test config**: campaign scopes, quiet hours, per-user channel preferences.
* **Results**: interaction transcripts, signals (clicked, replied, escalated), timestamps.
* **Audit**: every access, message/call, and tool invocation.

---

## 4) Orchestration & Agents

### 4.1 LangGraph (Workflows)

* **Start conditions**:

  * **Human-in-the-loop** (button/API) or **schedule** (cron/EventBridge rule).
* **Canonical flow**:

  1. **IngestSpec** → validate campaign scope & tenant.
  2. **TargetFetch** (via Database Tool) → returns opted-in users.
  3. **Planner** → fan-out per-user tasks to **SQS FIFO**.
  4. **PolicyGate** → enforce quiet hours, per-user/day caps, rate limits.
  5. **ChannelRouter** → pick channel (SMS, voice, Viber, device-fleet WhatsApp/Viber).
  6. **Dispatch** → channel worker sends; webhook response returns.
  7. **Analyzer** → LLM classifies response, updates **risk score**.
  8. **Writer** → persist results (Database Tool), emit metrics/events.

### 4.2 LangChain (Agents)

* **Persona Agent**: build **Conversational emulated threat actor** messages (LLM), bounded by deny-lists and safety filters.
* **Planner Agent**: selects channel/tool per target; handles retries/backoffs.
* **Analyst Agent**: classifies replies (intent/sentiment), decides next step.
* **All agents call only via MCP tools** (no direct SDK keys embedded).

---

## 5) MCP Tooling (Standardized Interfaces)

* `database.*` — `targets.list(tenantId, campaignId)`, `results.write(...)`, `consent.verify(userId)`.
* `scheduler.enqueue(task)` — puts per-user tasks on **SQS FIFO**; supports dedupe & DLQs.
* `cpaas.sms.send`, `cpaas.voice.call`, `cpaas.viber.send` — **CPaaS (Communications Platform as a Service)** adapters (e.g., Sinch/Vonage/Twilio).
* `devicefleet.whatsapp.send`, `devicefleet.viber.send` — controlled **Android device farm** path for high-fidelity **End-to-End Encryption (E2EE)** consumer app scenarios; phones provisioned with **eUICC (Embedded Universal Integrated Circuit Card)** via **RSP (Remote SIM Provisioning)**.
* `risk.emit(event)` — push signals to analytics/SIEM.

**Why MCP**: identical contracts across providers enable **channel failover** (e.g., WhatsApp policy changes → route to Viber/SMS/voice without touching agent logic).

---

## 6) Channels & Execution

### 6.1 Primary (API-first)

* **SMS & Voice**: **CPaaS** with high throughput, recording, webhooks, and compliance tooling.
* **Viber Business**: partner APIs for opted-in messaging; webhook responses.

### 6.2 Secondary (High-fidelity Consumer Apps)

* **Android device fleet** (not 500; right-sized) for WhatsApp/Viber consumer app tests that API channels can’t emulate.
* **eUICC/RSP** to provision numbers over-the-air, rotate or suspend identities, reduce physical handling.
* Optional **GSM–VoIP gateways** for voice density where hardware supports it.

---

## 7) Data & Message Contracts

### 7.1 CampaignSpec (submitted to Control Plane)

```json
{
  "tenantId": "acme",
  "campaignId": "cmp_2025_10_24_Q4",
  "channels": ["sms", "voice", "viber", "devicefleet_whatsapp"],
  "persona": {"name":"Vendor AP", "tone":"urgent-polite", "pretext":"invoice fix"},
  "policies": {"maxMsgsPerUserPerDay": 3, "quietHours": ["22:00-07:00"]},
  "guardrails": {"no_pii": true, "no_malware_links": true}
}
```

### 7.2 Queue Task (to SQS FIFO)

```json
{
  "tenantId": "acme",
  "userId": "u_123",
  "campaignId": "cmp_2025_10_24_Q4",
  "channel": "sms",
  "locale": "en-US",
  "attempt": 1,
  "personaId": "vendor_ap_v1",
  "conversationId": "conv_abc",
  "traceId": "tr_001"
}
```

### 7.3 Send Result (from channel worker)

```json
{
  "status": "sent|failed",
  "providerMessageId": "pmsg_789",
  "latencyMs": 320,
  "error": null,
  "tenantId": "acme",
  "userId": "u_123",
  "conversationId": "conv_abc",
  "timestamp": "2025-10-23T16:40:00Z"
}
```

---

## 8) Security & Compliance

* **PII segmentation**: **one RDS per tenant**; separate subnet groups and KMS keys optional. No shared schemas.
* **Secrets**: **AWS Secrets Manager**; rotate regularly; agents never see raw creds (only the Database Tool sees them).
* **Network**: Private subnets; **VPC endpoints** for RDS/Secrets; egress via NAT; strict Security Groups.
* **Content Safety**: Persona templates with deny-list enforcement; URL shortener/redirector that blocks disallowed destinations; explicit **opt-in** and **kill-switch** per campaign.
* **Audit**: Immutable event log for every tool call and message/call; export to **SIEM** and cold storage (S3 with Object Lock, lifecycle policies).

---

## 9) Scaling & Resilience

* **Concurrency**: Add **SQS consumers** (channel workers) to scale linearly; per-tenant pools ensure fairness.
* **Throughput**: Tune CPaaS account limits (messages per second); shard workers by tenant.
* **Retries/Backoff**: Exponential backoff with **dead-letter queues**; per-channel error budgets.
* **Multi-region** (optional): Active-active orchestrators; per-tenant data residency by deploying RDS in region of record.

---

## 10) Operations

* **Deploy**: GitOps pipeline to ECS/EKS; immutable images; environment per tenant segment or per stage (dev/stage/prod).
* **Runbooks**:

  * Campaign fails to start → check EventBridge rule & orchestrator health.
  * Elevated failures on a channel → pause channel adapter in **MCP** and reroute.
  * DB issues for a tenant → fail closed at Database Tool; alert, auto-quarantine campaign.

---

## 11) Minimal “Happy Path” Sequence

1. **Operator** clicks “Start Campaign” for tenant *ACME*.
2. **LangGraph** receives `campaign.created` → calls **Database Tool** `targets.list(ACME, campaignId)`.
3. **Planner** pushes tasks to **SQS FIFO** with `MessageGroupId="ACME:u_123"`.
4. **Workers** consume, **Persona Agent** generates text, **Channel Router** selects **SMS** (CPaaS) or **devicefleet_whatsapp**.
5. **Send** → webhooks return responses → **Analyst Agent** classifies outcome → **Writer** stores result via **Database Tool**.
6. **Metrics/Audit** reflect progress; risky behaviors trigger just-in-time training.

---

## 12) Why this meets the requirements

* **Scalable & robust**: SQS-backed workers, stateless agents, horizontal scale beyond **500 concurrent** users.
* **Compliant & safe**: Opt-in gating, per-tenant RDS isolation, auditable tool calls.
* **Channel-agnostic**: MCP tools insulate workflows from provider or Terms-of-Service shifts.
* **Minimal phones**: API-first for SMS/voice/Viber; **small device fleet** only where consumer app realism is essential, provisioned via **eUICC/RSP**.

## Multi-tenancy and Isolation

- **Data isolation**: One RDS PostgreSQL instance per tenant. Optional per-tenant subnet groups and KMS keys for stronger blast-radius control.
- **Access paths**: All data access is via MCP tools (e.g., `database.*`); agents never hold raw credentials. Tools resolve `{tenantId -> endpoint, creds, KMS}` via Secrets Manager.
- **IAM and least privilege**: Per-tenant IAM roles restrict RDS, SQS, and Secrets access to that tenant’s resources only. Infra-as-code templates stamp out identical-but-isolated stacks.
- **Queue partitioning**: SQS FIFO uses `MessageGroupId = {tenantId}:{userId}` to isolate ordering and throughput. Per-tenant consumers can be scaled independently for fairness.
- **Connection pooling**: Pool size quotas per tenant (e.g., pgbouncer or app-level pools) to prevent noisy neighbor DB connection exhaustion.
- **State and context**: `tenant_id` is mandatory in workflow state and tool inputs; deny-by-default when missing or mismatched. All audit events include `tenant_id` for attribution.

## Reliability: Retries, Idempotency, and DLQs

- **Idempotency keys**: All effectful tool calls (e.g., `cpaas.sms.send`) accept a caller-supplied `idempotency_key` and dedupe on the provider side and/or an internal store to avoid duplicate sends.
- **SQS FIFO semantics**: Use `MessageDeduplicationId` derived from `(tenantId, userId, conversationId, attempt)` to avoid duplicate task processing. Preserve per-user order via `MessageGroupId`.
- **Backoff and retry**: Exponential backoff with jitter for transient failures. Cap max attempts per channel and per campaign; escalate to DLQ after threshold.
- **Dead-letter queues (DLQs)**: Each FIFO queue has a paired DLQ. Define triage runbooks for replay, fix-forward, or quarantine per failure class. Emit SIEM events on DLQ drops.
- **Exactly-once outcomes**: Writers persist with idempotent upserts keyed by `(tenantId, userId, conversationId, providerMessageId|idempotency_key)`.
- **Webhook replays**: Verify signatures and timestamps; reject late or duplicate webhooks using a nonce table with TTL to prevent reprocessing.

---

## Future Extensions

* Add adapters for **Telegram**, **Rich Communication Services (RCS)**, **email**, **Microsoft Teams/Slack** DMs.
* Real-time **voice agents** via CPaaS **WebSocket** media streams.
* **Feature store** for cross-campaign user risk signals; offline model training to improve targeting.

---

### Appendix: Component Inventory

* **Control Plane**: Next.js UI + Admin API.
* **Orchestrator**: LangGraph service (Python/JS).
* **Agents**: LangChain workers (Persona/Planner/Analyst).
* **MCP Tools**: `database`, `scheduler`, `cpaas.*`, `devicefleet.*`, `risk`.
* **Databases**: One **RDS PostgreSQL** per customer.
* **Queues**: **SQS FIFO** (+ DLQs).
* **Secrets**: **AWS Secrets Manager**.
* **Keys**: **AWS KMS**.
* **Monitoring**: CloudWatch + SIEM integration.
* **Device Fleet (optional)**: Android phones with **eUICC (RSP)**; mobile device management & automation harness.
