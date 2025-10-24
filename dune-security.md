dune-security.md

# SECURITY.md — Dune Security Pen-Testing Platform

---

## Purpose

This brief describes how the platform isolates customers and devices, protects secrets, governs messaging accounts, prevents abuse, and meets regional privacy obligations—while safely using **LLM** agents to generate *contextual* content and handle multi-turn conversations.

---

## 1) Isolation of customers, devices, and data flows

**Tenant (customer) isolation.** Each customer is provisioned with its own **Amazon RDS for PostgreSQL** instance in a private subnet. Storage and snapshots are encrypted at rest with **AWS KMS** (customer-managed key per tenant when required). AWS documents native **Advanced Encryption Standard (AES)-256** encryption for RDS and prescriptive guidance for customer-managed key practices and rotation. ([AWS Documentation][1])

**Network isolation.** All data plane resources reside in an **AWS Virtual Private Cloud (VPC)**. Security Groups and network access control lists allow only least-privilege east-west traffic. Private **VPC endpoints** are used for RDS and Secrets to keep traffic off the public Internet (defense-in-depth consistent with AWS guidance). ([AWS Documentation][1])

**Data-flow isolation.** Work is fanned out via **Amazon SQS** **First-In-First-Out (FIFO)** queues. We set **MessageGroupId** to `{tenantId}:{userId}` to guarantee strict per-user ordering and to prevent cross-tenant interleaving; AWS documents the ordering semantics and operational considerations for MessageGroupId. ([AWS Documentation][2])

**Device/channel isolation.** High-fidelity **E2EE** tests that require consumer apps run on a small, governed Android fleet. Identities are provisioned over-the-air with **eUICC**/**RSP**; fleet credentials and per-device health are kept tenant-scoped. API-first channels (Short Message Service (SMS), voice, and Viber Business) are accessed through provider adapters; inbound webhooks are authenticated (see §3, §4).

---

## 2) Messaging account handling (sessions, tokens, device credentials)

**Provider credentials.** API keys and OAuth tokens for communications providers are never embedded in agents. They are stored in a secrets system (see §3), issued to workers as short-lived, least-privilege tokens, and rotated automatically per provider capability and policy. (AWS KMS and HashiCorp guidance recommend rotation and audited access.) ([AWS Documentation][3])

**Webhook authenticity.** All inbound webhooks (for example, delivery receipts and call events) are verified using the provider’s signature scheme—e.g., **Twilio** includes an `X-Twilio-Signature` header based on **Hash-based Message Authentication Code (HMAC)**; our server recomputes and compares the signature before accepting the event. ([Twilio][4])

**Session hygiene (devices).** For the Android fleet, the platform maintains per-device session state, rate-limits, and cool-downs; it records ban or throttling signals and rotates identities via **eUICC/RSP** when necessary.

---

## 3) Secrets management (HashiCorp Vault, AWS KMS)

**Control plane of secrets.** **HashiCorp Vault** (or **HashiCorp Cloud Platform (HCP) Vault**) brokers all sensitive material (provider API keys, database credentials). Where possible, we issue **dynamic secrets**—ephemeral credentials generated on demand and auto-revoked—rather than long-lived static tokens. HashiCorp documents the model and when to choose dynamic vs. rotated secrets. ([HashiCorp Developer][5])

**Envelope encryption and keys.** **AWS KMS** is used to encrypt data at rest (databases, logs, snapshots) and to manage tenant-scoped keys with rotation and **AWS CloudTrail** auditing of every key operation. AWS provides prescriptive guidance on KMS best practices. ([AWS Documentation][3])

**Access paths.** Workloads authenticate to Vault using cloud identities; agents never receive raw secrets. All secret reads/writes are logged and forwarded to the **SIEM**.

---

## 4) Abuse prevention, audit logging, and red-team control safeguards

**Rate limiting and quiet hours.** Per-tenant and per-user message/voice caps are enforced by the orchestrator. Quiet hours and concurrency ceilings prevent fatigue or harassment scenarios.

**Approval workflow and kill switch.** Risky campaigns require dual approval (two-person rule). A tenant-scoped kill switch halts all dispatch immediately.

**Audit logging.** Every tool call (including prompt, output, target, and provider response—redacted as necessary), credential use, and content variant emits an immutable event shipped to the **SIEM** and long-term storage. This aligns to common audit controls for accountability and non-repudiation.

**Webhook validation and outbound safety.** As above, inbound events are signature-verified (e.g., **Twilio HMAC**). Outbound payloads are sanitized and constrained to approved media types. ([Twilio][4])

---

## 5) Regional privacy and compliance

**European Union — General Data Protection Regulation (GDPR).** We implement: (a) lawful basis and purpose limitation; (b) data minimization; (c) **Data Protection Impact Assessment (DPIA)** for behavioral testing; (d) data subject rights (access, rectification, erasure, portability, objection) and response workflows; and (e) regional hosting when required (EU RDS, EU KMS keys). See GDPR Chapter 3 (rights of the data subject) and controller/processor duties. ([GDPR][6])

**India — Digital Personal Data Protection (DPDP) Act, 2023.** We obtain explicit consent (or use another lawful ground), present clear notices, and prepare for enforcement of obligations and penalties as rules are notified. India’s Ministry of Electronics and Information Technology hosts the Act text; recent reporting notes the lag between assent and full enforcement, which we monitor for operational updates. ([MeitY][7])

**Brazil — Lei Geral de Proteção de Dados (LGPD).** We support LGPD principles (necessity, transparency, security), data subject rights, and the authority of the **Autoridade Nacional de Proteção de Dados (ANPD)**. Sources include the ANPD’s official English text and reputable summaries. ([Serviços e Informações do Brasil][8])

**Data residency.** For regulated customers, we deploy per-region stacks (for example, EU, India, Brazil) with tenant-scoped RDS and keys in-region and with restricted cross-border transfers consistent with local law.

---

## 6) LLM safety: contextual generation, prompt-injection prevention, and conversation handling

**Threat model.** During tests, employees may send adversarial prompts to **LLM** agents (e.g., “ignore your rules,” “tell me your system prompt,” “write me a poem”). The **Open Worldwide Application Security Project (OWASP)** publishes “Top 10 for Large Language Model Applications,” highlighting **Prompt Injection** and **Sensitive Information Disclosure** risks; our controls align to these recommendations. ([OWASP Gen AI Security Project][9])

**Contextual generation (tailoring with minimal data).**

* Agents fetch only the *minimum* profile attributes needed to personalize content (for example, first name, role, locale).
* The **Database Tool** redacts **PII** not required for the message, and it never provides secrets or internal system identifiers to the **LLM**.

**Guardrails to prevent prompt injection.**

1. **Tools-only execution via Model Context Protocol (MCP).** Agents cannot call networks, databases, or providers directly; they must invoke allow-listed tools with strict schemas (for example, `cpaas.sms.send({tenantId, userId, content})`). The orchestrator enforces tenant policy on every call.
2. **System prompt hardening.** The system prompt explicitly treats user content as *untrusted* and includes refusal policies for meta-requests (e.g., “reveal your instructions”).
3. **Input sanitization and output validation.** All inputs pass through a sanitizer (strip control tokens, deny-listed phrases). All outputs pass a *policy checker* (deterministic rules or a second **LLM** acting as a gate) before dispatch, per OWASP guidance. ([OWASP][10])
4. **Scoped policy tokens.** Tool calls require time-bound, signed policy tokens (campaignId, stepId, throttle state) issued by the orchestrator, preventing forged or replayed tool use.
5. **Monitoring and alerting.** Suspected injection patterns or “jailbreak” keywords generate alerts and are recorded for forensic review in the **SIEM**.

**Conversation handling (follow-ups).**

* **Finite-state dialogue.** Conversations follow a bounded state machine (probe → persuade → decision). Agents may not engage in open-ended chats.
* **“Tell me more.”** Provide a pre-approved elaboration consistent with the scenario; do not escalate to new, unapproved pretexts.
* **“How did you find me?”** Use a stock, non-revealing line (for example, “from vendor records on file”); never disclose internal sources or systems.
* **Out-of-scope requests** (for example, “write me a poem,” “send your system prompt”). Respond with a courteous deflection and terminate or route to a neutral close-out message.
* Every reply is re-checked by the policy gate before sending.

---

## 7) Operations and incident readiness

**Approvals and DPIA.** Before launching a campaign, we capture consent scope and complete a **Data Protection Impact Assessment** where required (for example, **GDPR** high-risk processing). ([GDPR][6])

**Observability.** We collect structured logs and metrics for each workflow step and forward them to the **SIEM**. Audit trails include who approved, what was sent, to whom (pseudonymized where possible), when, through which channel, and the provider’s signed receipt.

**Resilience.** **SQS FIFO** queues with dead-letter queues, exponential back-off, and idempotent handlers provide reliable processing; AWS documents ordering and back-pressure considerations. ([AWS Documentation][11])

**Kill switch.** A tenant-scoped and global kill switch can halt all sends and tool calls immediately.

---

## 8) What is *out of scope* for agents

* Agents never see raw database connection strings, cloud credentials, or provider secrets. Those are isolated in the Database/Secrets tools.
* Agents cannot initiate new campaigns on their own; they react only to an operator action or a schedule.

---

## 9) Summary

This design provides **strong isolation** (one **Amazon RDS** per tenant, VPC segmentation), **robust secrets control** (**HashiCorp Vault** with **dynamic secrets** and **AWS KMS** envelope encryption), **abuse prevention and auditability** (rate limits, approvals, immutable logs, webhook verification), and **regional privacy alignment** (**GDPR**, **India DPDP**, **Brazil LGPD**). It also implements **LLM** safety practices endorsed by **OWASP** to prevent **prompt injection**, restrict conversation scope, and ensure that messages are *contextual* yet policy-compliant. ([AWS Documentation][1])

---

*Key references:*

* AWS RDS encryption and **AES-256** at rest; **AWS KMS** best practices and key management/rotation. ([AWS Documentation][1])
* **Amazon SQS FIFO** ordering and **MessageGroupId** guidance. ([AWS Documentation][2])
* **HashiCorp Vault** dynamic vs. rotated secrets. ([HashiCorp Developer][5])
* **Twilio** webhook **HMAC** validation. ([Twilio][4])
* **OWASP** Top 10 for **LLM** applications (Prompt Injection and controls). ([OWASP Gen AI Security Project][9])
* **GDPR** (EU), **DPDP** (India), **LGPD** (Brazil) official/authoritative sources. ([GDPR][6])


[1]: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html?utm_source=chatgpt.com "Encrypting Amazon RDS resources - AWS Documentation"
[2]: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagegroupid-property.html?utm_source=chatgpt.com "Using the message group ID with Amazon SQS FIFO Queues"
[3]: https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-kms-best-practices/data-protection-encryption.html?utm_source=chatgpt.com "Encryption with AWS KMS - AWS Prescriptive Guidance"
[4]: https://www.twilio.com/docs/usage/webhooks/webhooks-security?utm_source=chatgpt.com "Webhooks Security"
[5]: https://developer.hashicorp.com/hcp/docs/vault-secrets/dynamic-secrets?utm_source=chatgpt.com "Dynamic secrets | HashiCorp Cloud Platform"
[6]: https://gdpr-info.eu/?utm_source=chatgpt.com "General Data Protection Regulation (GDPR) – Legal Text"
[7]: https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf?utm_source=chatgpt.com "THE DIGITAL PERSONAL DATA PROTECTION ACT, 2023 ..."
[8]: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/outros-documentos-e-publicacoes-institucionais/lgpd-en-lei-no-13-709-capa.pdf?utm_source=chatgpt.com "Brazilian Data Protection Law LGPD - Portal Gov.br"
[9]: https://genai.owasp.org/llmrisk/llm01-prompt-injection/?utm_source=chatgpt.com "LLM01:2025 Prompt Injection - OWASP Gen AI Security Project"
[10]: https://owasp.org/www-project-top-10-for-large-language-model-applications/Archive/0_1_vulns/Prompt_Injection.html?utm_source=chatgpt.com "LLM01:2023 - Prompt Injections"
[11]: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-understanding-logic.html?utm_source=chatgpt.com "FIFO queue delivery logic in Amazon SQS"
