# Feature Specification: Fix Agent Answer Relevance for Technology Queries

**Feature Branch**: `005-fix-agent-answer-relevance`
**Created**: 2026-02-26
**Status**: Draft
**Input**: Agent includes irrelevant facts in technology-specific answers. When asking "какой опыт с компьютерным зрением", the answer includes "LLM+RAG assistant for fines calculation" which is NOT related to computer vision. Root causes: (1) normalizer does not filter individual facts by content relevance — operates at document-type level only; (2) GigaChat agent re-synthesizes answer from raw `rendered_facts` instead of using the pre-generated deterministic `answer` field; (3) deterministic answer for `technology_usage` is too brief, prompting the agent to "improve" it.

## Clarifications

### Session 2026-02-26

- Q: Should content-level filtering apply to intents beyond `technology_usage`? → A: Only `technology_usage` — this is the only intent where user asks about a SPECIFIC technology but retrieves a project with MIXED technologies. Other intents (project_details, experience_summary) inherently want ALL achievements for a given project/company.
- Q: When reducing information surface (FR-006), should there be a fallback if deterministic answer fails? → A: Conditional surface reduction — only remove `rendered_facts`/`items` when deterministic answer was successfully generated. When answer falls back to LLM, keep full context for the agent.
- Q: How should content filtering handle multilingual entity names (English entity "Computer Vision" vs Russian text "компьютерного зрения")? → A: Filtering MUST use multiple criteria: entity name from plan + keywords from original user question + related technology names from project metadata. FR-002 updated to reflect this.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Technology-specific answers contain only relevant achievements (Priority: P1)

A user asks the portfolio agent about experience with a specific technology domain (e.g., "какой опыт с компьютерным зрением"). The agent MUST return only achievements and details directly related to that technology domain, filtering out unrelated achievements from the same project. Currently, the project "t2 — Нейросети" has mixed achievements (CV + LLM+RAG + MLOps + Backend), and the agent returns ALL of them instead of only the CV-related ones.

**Why this priority**: This is the core user-facing bug. Irrelevant facts in answers undermine trust and professionalism. A recruiter asking about computer vision experience should not see "LLM assistant for fines calculation" in the answer.

**Independent Test**: Ask "какой опыт с компьютерным зрением" and verify the answer mentions CV-related achievements (brand recognition service, CV model training/inference) but does NOT mention LLM+RAG assistant for fines or Backend/FastAPI integrations.

**Acceptance Scenarios**:

1. **Given** the portfolio project "t2 — Нейросети" contains 4 achievements (CV service, LLM+RAG assistant, MLOps pipeline, Backend), **When** user asks "какой опыт с компьютерным зрением", **Then** the answer includes ONLY CV-related achievements (brand recognition service, CV model training/inference MVP, MLOps for CV models) and does NOT include the LLM+RAG assistant.
2. **Given** the same portfolio data, **When** user asks "опыт с LLM и RAG", **Then** the answer includes ONLY the LLM+RAG assistant achievement and does NOT include the CV brand recognition service.
3. **Given** a project with only one achievement related to the queried technology, **When** user asks about that technology, **Then** the answer includes that single achievement with project context (project name, company, period).

---

### User Story 2 - Agent uses pre-generated answer without re-synthesis (Priority: P1)

When the RAG pipeline's internal tool (`portfolio_rag_tool`) generates a deterministic answer, the agent MUST relay that answer to the user without re-synthesizing from raw data. Currently, the GigaChat agent LLM sees the full `rendered_facts` JSON field (which contains all project details) and produces its own version of the answer, incorporating irrelevant information.

**Why this priority**: Even if the normalizer and answer generator produce a perfect, relevant answer, the agent LLM can still inject irrelevant facts from `rendered_facts`. This is the second layer of the bug and must be fixed alongside content filtering.

**Independent Test**: Send a technology query where the deterministic answer is concise and relevant. Verify the final streamed response to the user matches the deterministic answer content, not a re-synthesized version with additional details from `rendered_facts`.

**Acceptance Scenarios**:

1. **Given** `portfolio_rag_tool` returns `{"answer": "relevant answer text", "rendered_facts": "...full details..."}`, **When** the agent LLM processes the tool result, **Then** the agent outputs the `answer` field value to the user without adding information from `rendered_facts`.
2. **Given** the deterministic answer is "Дмитрий применял Computer Vision в проекте t2 — Нейросети (Aston, 2024-2025): [CV-related achievements]", **When** the agent formats the response, **Then** no LLM+RAG or Backend achievements appear in the final user-facing message.
3. **Given** the deterministic answer generator cannot produce an answer (falls back to LLM), **When** the agent receives the tool result, **Then** the LLM-generated answer from the `answer` field is still used as-is.

---

### User Story 3 - Rich deterministic answers for technology_usage intent (Priority: P2)

The deterministic answer generator for `technology_usage` intent produces overly brief answers (e.g., "Дмитрий применял Computer Vision в проектах: t2 — Нейросети" — just a project name). The answer MUST include specific achievements related to the queried technology, providing enough detail that the agent LLM has no reason to "improve" it.

**Why this priority**: The brief answer is a contributing factor to the agent re-synthesizing. If the deterministic answer included relevant achievements, even a re-synthesizing agent would produce a relevant response. This also improves user experience directly.

**Independent Test**: Ask "какой опыт с компьютерным зрением" and verify the deterministic answer (before agent processing) includes specific CV-related achievements from the project, not just the project name.

**Acceptance Scenarios**:

1. **Given** the normalizer passes CV-related facts for "t2 — Нейросети", **When** the deterministic answer generator runs for `technology_usage` intent, **Then** the answer includes specific achievements (e.g., "Внедрил сервис компьютерного зрения для ребрендинга t2/Tele2", "Разработал MVP бэкенда авто-обучения и инференса CV-моделей").
2. **Given** multiple projects use the queried technology, **When** the deterministic answer is generated, **Then** achievements from each relevant project are listed under their project name.
3. **Given** a technology appears in the graph but has no detailed achievements in retrieved documents, **When** the deterministic answer is generated, **Then** the answer falls back to listing project names (current behavior) rather than failing.

---

### Edge Cases

- What happens when ALL achievements in a project are relevant to the queried technology? The system should return all of them (no filtering needed).
- What happens when NO achievements in a retrieved project match the queried technology? The project should be excluded from the answer entirely, even if the project document was retrieved by semantic search.
- What happens when the technology is a broad domain (e.g., "Machine Learning") that spans multiple sub-achievements? The system should include all ML-related achievements, erring on the side of inclusion for ambiguous cases.
- What happens when the user asks about a technology that does NOT exist in the portfolio? The system should clearly state that no experience was found (existing behavior, should not regress).
- What happens when the agent LLM is changed from GigaChat to a different provider? The fix for answer relay must work regardless of the agent LLM provider.
- What happens when the planner entity name is in English ("Computer Vision") but document text is in Russian ("компьютерного зрения")? The content filter must use keywords from the user's original question as additional matching criteria, ensuring multilingual coverage.
- What happens when the deterministic answer generator fails (returns None) and the LLM fallback is used? The full `rendered_facts` and `items` must remain available to the agent LLM — surface reduction only applies when a deterministic answer exists.
- What happens when a bullet point mentions multiple technology domains (e.g., "MLOps pipeline for CV models")? The bullet should be included for BOTH "MLOps" and "Computer Vision" queries — err on the side of inclusion when a bullet references the queried technology even partially.

## Requirements *(mandatory)*

### Functional Requirements

**Content-level relevance filtering (normalizer/answer layer):**

- **FR-001**: When processing facts for `technology_usage` intent, the system MUST filter individual text segments (bullet points/achievements) within documents by relevance to the queried technology, not just filter by document type.
- **FR-002**: The filtering MUST use multiple matching criteria to determine content relevance: (a) the technology entity name from the planner (e.g., "Computer Vision"), (b) keywords from the user's original question (e.g., "компьютерное зрение"), and (c) related technology names from the project's metadata (e.g., "Detectron2", "YOLO" for CV). This ensures multilingual matching and coverage of related frameworks/tools.
- **FR-003**: Text segments that do not mention or relate to the queried technology MUST be excluded from the answer, even if they come from a project that is related to the technology.
- **FR-004**: The filtering MUST preserve project context (project name, company, period) when including relevant segments.

**Agent answer relay (preventing re-synthesis):**

- **FR-005**: When the RAG tool returns a result with a non-empty `answer` field, the agent MUST use that answer as the final response without adding, removing, or rephrasing information from other fields in the tool output.
- **FR-006**: The information surface available to the agent LLM from tool results MUST be conditionally minimized: when a deterministic answer is successfully generated, `rendered_facts` and raw `items` fields MUST NOT be exposed to the agent. When the answer falls back to LLM generation (no deterministic answer available), the full context MUST be preserved for the agent to work with. This prevents regression for non-deterministic intents while solving re-synthesis for deterministic ones.
- **FR-007**: The system MUST still allow the agent to process the answer for formatting purposes (e.g., markdown rendering), but MUST NOT allow injection of new factual claims.

**Deterministic answer enrichment:**

- **FR-008**: The deterministic answer for `technology_usage` intent MUST include specific achievements/descriptions related to the queried technology, not just project names.
- **FR-009**: The deterministic answer MUST structure information as: project name + company + period + relevant achievements (bullet points).
- **FR-010**: If no specific achievements can be extracted, the system MUST fall back to the current behavior (project name listing) rather than producing an empty answer.

**Non-regression:**

- **FR-011**: All existing normalizer rules for other intents (contacts, project_details, project_list, etc.) MUST continue to work unchanged.
- **FR-012**: The fix MUST NOT increase response latency by more than 10% for technology-related queries.
- **FR-013**: Plan cache MUST be cleared after deployment to avoid serving stale cached plans.

### Key Entities

- **FactItem**: A retrieved document with `type`, `text` (full content), and `metadata`. Currently, an entire project or experience_project document is stored as a single FactItem. The filtering must operate within the `text` field to extract relevant segments.
- **QueryPlanV3**: The planner's output containing `intents`, `entities` (with technology names), and `tool_calls`. The entity names provide the filtering criterion for content relevance.
- **FactsPayload**: Container passed to the answer generator with filtered `items`, `intents`, `evidence_text`, and rendering instructions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the query "какой опыт с компьютерным зрением", the agent's response includes CV-related achievements (brand recognition, CV model training) and excludes LLM+RAG assistant for fines — 100% of the time across 5 repeated tests.
- **SC-002**: For the query "опыт с LLM и RAG", the response includes LLM+RAG achievements and excludes CV brand recognition — verifying bidirectional filtering works.
- **SC-003**: The agent's final streamed response matches the content of the deterministic `answer` field — no additional facts from `rendered_facts` appear that were not in the `answer`.
- **SC-004**: The deterministic answer for `technology_usage` includes at least one specific achievement per relevant project, not just the project name.
- **SC-005**: All existing tests pass without modification (no regression).
- **SC-006**: Response latency for technology queries remains within 10% of current performance.

### Assumptions

- The planner correctly identifies the `technology_usage` intent and extracts the technology entity from the user's question. This has been verified in logs and is not part of this fix.
- The hybrid search retrieves documents that contain the relevant technology information (the t2 project documents ARE retrieved). The issue is post-retrieval filtering, not search quality.
- "Computer Vision" as a concept is handled correctly by the planner entity extraction (entity `technology:computer-vision`). The graph may or may not have a matching node — this is acceptable.
- The `experience` and `experience_project` document types are already included in the normalizer type whitelist (fixed in spec 004). This spec addresses the deeper problem of content-level filtering within those documents.
- The GigaChat agent model's tendency to re-synthesize from raw data is a known behavioral characteristic that cannot be fully eliminated by prompt engineering alone — a structural fix (reducing information surface) is required.
