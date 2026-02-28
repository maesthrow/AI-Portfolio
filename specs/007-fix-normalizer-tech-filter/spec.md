# Feature Specification: Fix Normalizer technology_usage Filter Dropping Relevant Facts

**Feature Branch**: `007-fix-normalizer-tech-filter`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "RAG agent answers 'нет информации' to questions about AI agents experience, despite portfolio containing this data. Root cause: normalizer's technology_usage_filter drops profile-type facts, and concept-level terms like 'AI-агенты' are not represented as Technology entities in the knowledge graph."

## Problem Statement

When a user asks the RAG agent "какой опыт с ИИ агентами" (what experience with AI agents), the agent incorrectly responds "В портфолио Дмитрия нет упоминаний опыта работы с ИИ агентами" (no mentions of AI agent experience), despite the portfolio clearly containing this information in multiple places:
- Profile: subtitle "AI-агенты", current_position "AI-агенты для Сбера (аутстаффинг)"
- Profile summary: "архитектура агентных систем"
- Focus areas: "LLM / AI-Agents / RAG" with detailed bullet points about agent scenarios

### Root Cause Chain (3 layers)

**Layer 1 — Knowledge Graph miss**: The planner generates entity `technology:ai-agents`, but no TECHNOLOGY node with slug `ai-agents` exists in the graph. "AI-агенты" is a concept mentioned in the profile and focus areas, but never registered as a Technology entity in content-api. The graph query returns 0 facts.

**Layer 2 — Normalizer over-filtering**: On fallback to hybrid search, the profile document (score 0.15, highest relevance) is correctly retrieved but then **dropped** by the `technology_usage_filter` rule, which only allows types: `technology_usage`, `technology`, `project`, `experience`, `experience_project`. The `profile` type is excluded. After filtering, only irrelevant experience documents (РКЦ Прогресс, Спарго, АЛОР) remain — none mention AI agents.

**Layer 3 — Content gap in experience documents**: The Aston experience (the actual workplace where AI agent work happened) mentions "LLM/RAG-системы и CV-сервисы" but never uses the term "AI-агенты" or "AI agents", so hybrid search cannot find it either. The profile.current_position "AI-агенты для Сбера (аутстаффинг)" is the only source linking the developer to AI agents work.

### Related Case: "машинное обучение" vs "ML" Quality Gap

A second manifestation of the same root cause occurs with ML queries. When a user asks "какой опыт с машинным обучением" (what ML experience), the planner classifies this as `experience_summary` intent (NOT `technology_usage`), so the restrictive `technology_usage_filter` is NOT triggered. The normalizer applies `experience_prioritization` instead, preserving all 10 facts. However, the answer is generic — it lists all work experience without focusing on ML.

When the same user asks "какой опыт с ML", the planner also classifies as `experience_summary`, and the answer is significantly better: it includes the `tech_focus` document ("ML и CV — Машинное обучение, компьютерное зрение: PyTorch, Ultralytics, YOLO, Detectron2, OpenCV, NumPy, Pandas") which provides focused technical context.

**Key insight**: The `tech_focus` document type (score 0.004 in search) contains crucial technology skills data. If these queries were classified as `technology_usage` instead (which would be semantically correct), the `tech_focus` document would be **dropped** by the type filter — exactly the same bug as the AI agents case. The current "working" behavior is accidental: it only works because the planner happens to route ML queries to a less restrictive intent path.

**Root cause is shared**: Both cases stem from the normalizer's `technology_usage_filter` being too restrictive. The filter excludes `profile`, `focus_area`, `tech_focus`, and `catalog` types — all of which contain technology competency data that is directly relevant to "what experience do you have with X?" questions.

### Impact

This is a critical quality defect — the agent denies the developer's **primary competency** (AI agents) to portfolio visitors. Similar failures would occur for any concept-level query that maps to profile/focus_area/tech_focus data rather than explicit Technology entities. The ML case demonstrates that even when the answer technically works, it's fragile and depends on the planner choosing a non-restrictive intent path.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Concept-level technology query returns relevant answer (Priority: P1)

A portfolio visitor asks the RAG agent about the developer's experience with a concept-level skill (e.g., "AI агенты", "машинное обучение", "NLP") that is described in the profile but not registered as a standalone Technology entity. The agent should find and present relevant information from across all document types.

**Why this priority**: This is the core bug — the agent denies the developer's primary competency. Every visitor asking about AI agents gets a wrong answer.

**Independent Test**: Can be tested by asking "какой опыт с ИИ агентами" and verifying the answer includes profile information about AI agent work (current position, summary, focus areas).

**Acceptance Scenarios**:

1. **Given** the portfolio contains profile with "AI-агенты для Сбера (аутстаффинг)" in current_position, **When** user asks "какой опыт с ИИ агентами", **Then** the agent answers with relevant information from the profile and any related experience/focus data — NOT "нет информации".
2. **Given** the portfolio contains focus area "LLM / AI-Agents / RAG" with bullet points, **When** user asks "что умеет делать с AI-агентами", **Then** the agent includes focus area details in the answer.
3. **Given** the hybrid search returns a profile document with high relevance score, **When** the normalizer processes facts for technology_usage intent, **Then** the profile document is preserved in the filtered results (not dropped by type filter).

---

### User Story 2 - Normalizer preserves high-relevance profile facts for technology queries (Priority: P1)

When the normalizer processes facts for a `technology_usage` intent query, high-relevance profile documents that contain the queried technology/concept in their content should not be dropped purely based on document type.

**Why this priority**: The normalizer type filter is the direct technical cause of the bug. Without this fix, even if search finds the right document, it gets discarded.

**Independent Test**: Can be tested by verifying that after normalizer processing, profile-type facts mentioning the queried technology remain in the filtered output.

**Acceptance Scenarios**:

1. **Given** a set of 8 facts including a profile doc with score 0.15 mentioning "AI-агенты", **When** the normalizer applies `technology_usage_filter`, **Then** the profile fact is retained (not filtered out).
2. **Given** a profile fact that does NOT mention the queried technology at all, **When** the normalizer processes it for technology_usage, **Then** it is correctly filtered out (no false positives).
3. **Given** the normalizer receives facts with entity_names=["AI agents"], **When** content-level filtering (Rule 2b) runs, **Then** the profile fact passes because it contains matching keywords ("AI-агент" in its text).

---

### User Story 3 - ML/technology queries include tech_focus data (Priority: P1)

When a user asks about machine learning experience, the answer should include the `tech_focus` document ("ML и CV") which lists specific tools (PyTorch, YOLO, Detectron2, etc.). This data must survive normalizer filtering regardless of whether the planner routes the query to `technology_usage` or `experience_summary` intent.

**Why this priority**: The `tech_focus` document type contains structured technology competency data (tools, frameworks, categories) that is essential for answering technology-related questions. If the planner changes its routing behavior (e.g., classifies "машинное обучение" as `technology_usage` instead of `experience_summary`), the answer quality would degrade due to the type filter.

**Independent Test**: Can be tested by asking "какой опыт с машинным обучением" and verifying the answer includes specific ML tools (PyTorch, YOLO, etc.) from the tech_focus document.

**Acceptance Scenarios**:

1. **Given** the portfolio contains a `tech_focus` document "ML и CV" listing PyTorch, YOLO, Detectron2, OpenCV, NumPy, Pandas, **When** user asks "какой опыт с машинным обучением", **Then** the answer includes these specific ML tools — not just generic experience listings.
2. **Given** the normalizer processes facts for `technology_usage` intent, **When** a `tech_focus` fact is present in the input, **Then** the `tech_focus` fact is retained (not filtered by type).
3. **Given** the planner classifies an ML query as either `technology_usage` or `experience_summary`, **When** the normalizer runs, **Then** the `tech_focus` document survives filtering in both cases.

---

### User Story 4 - Broader concept queries also work correctly (Priority: P2)

Portfolio visitors may ask about other concept-level skills that similarly appear primarily in the profile or focus areas: "опыт с RAG", "знание компьютерного зрения", "что знает про NLP". These should also return correct answers even when the concept doesn't perfectly match a Technology entity slug.

**Why this priority**: Ensures the fix is systematic, not just a one-off patch for "AI agents". The same pattern applies to other concepts.

**Independent Test**: Can be tested by asking about various concepts and verifying the agent finds relevant information from profile, focus areas, and tech_focus documents.

**Acceptance Scenarios**:

1. **Given** the portfolio lists "RAG" as both a Technology entity AND in focus areas, **When** user asks "расскажи про опыт с RAG", **Then** the answer includes both technology usage data AND profile/focus area context.
2. **Given** "Computer Vision" is a Technology entity but also detailed in focus areas and tech_focus, **When** user asks "какой опыт с компьютерным зрением", **Then** both structured graph data and unstructured focus area/tech_focus data are included.

---

### Edge Cases

- What happens when a profile fact mentions the technology in subtitle/metadata but not in the main text body? — Content keyword matching should check the full document text including subtitle, current_position, and summary fields.
- What happens when normalizer filtering would remove ALL facts, leaving 0 results? — The normalizer should have a safety mechanism: if type-filtering removes everything, fall back to returning unfiltered results. Note: the existing code already has an `if tech_facts:` guard that prevents zero-result scenarios; FR-003 makes this explicit and resilient.
- What happens when the queried concept has multiple spellings/translations? (e.g., "ИИ агенты" vs "AI agents" vs "AI-агенты") — Content keyword matching should handle common variations via the existing `TECH_ABBREVIATIONS` mapping.
- What happens if `entity_names` is empty or None? — Content-level filtering (Rule 2b) should be skipped, but type-level filtering should still apply with the expanded type list. In practice, `entity_names` is always populated for `technology_usage` intent because the planner must generate a technology entity for the graph query.
- What happens when a specific technology query (e.g., "где используется PostgreSQL") triggers expanded type filter? — Profile/focus_area/tech_focus facts that do NOT contain the keyword are rejected by Rule 2b content filtering. Only facts whose text actually mentions the queried technology survive. No false positives introduced.
- What happens with the deterministic `_answer_technology_usage` path in AnswerLLM when profile/focus_area/tech_focus facts are present? — These fact types lack the metadata structure expected by the deterministic path (no `technology`/`project` keys, no `project_names`), so they are safely ignored. If deterministic rendering produces no result, the LLM path takes over and benefits from seeing the additional context.

### Regression Safety Analysis

The proposed changes (FR-001 through FR-005) affect ONLY the `technology_usage` intent path in the normalizer. No other intents or pipeline components are modified. Key safety guarantees:

1. **Other intents unaffected**: Rules 1 (`technology_overview`) and 3 (`experience_summary`) are not touched. The type filter expansion is gated by `if intent_str == "technology_usage"`.
2. **Content-level filtering (Rule 2b) prevents false positives**: Even with expanded type list, each fact must pass keyword matching against the queried technology. Facts that don't mention the queried term are rejected regardless of type.
3. **Deterministic answer path is safe**: `_answer_technology_usage` in AnswerLLM ignores facts without structured `technology`/`project` metadata. New fact types (profile, focus_area, tech_focus) do not produce incorrect technology-to-project mappings.
4. **Zero-result fallback is conservative**: FR-003 preserves existing behavior (the `if tech_facts:` guard already prevents empty results) and makes it explicit. Expanding the type list makes zero-result scenarios even less likely.
5. **TECH_ABBREVIATIONS scope is narrow**: FR-004 adds only AI-agent-related terms, which are unambiguous in the portfolio context (no "insurance agent" or other non-AI uses of "агент").
6. **Existing tests serve as regression gate**: SC-004 requires all existing tests to pass without modification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The normalizer's `technology_usage_filter` MUST include `profile`, `focus_area`, and `tech_focus` in the list of allowed document types, in addition to the existing types (`technology_usage`, `technology`, `project`, `experience`, `experience_project`).
- **FR-002**: When content-level bullet filtering (Rule 2b) processes a `profile`-type fact, it MUST check the full document text (including metadata fields like subtitle, current_position, summary) for keyword matches — not just bullet points.
- **FR-003**: The normalizer MUST implement a safety fallback: if type-based filtering reduces the fact count to 0, it MUST return the original unfiltered facts (before type filtering was applied) rather than an empty list.
- **FR-004**: The existing `TECH_ABBREVIATIONS` mapping MUST be extended with an entry for "AI Agents" to support cross-language matching: covering Russian translations like "AI-агенты", "ИИ-агенты", "агентные системы".
- **FR-005**: The `technology_usage_filter` MUST also include `catalog` type documents, since `technologies_all` and `technologies_by_company` catalogs contain relevant usage information.

### Key Entities

- **FactItem**: A single piece of evidence retrieved by the RAG pipeline. Has `type` (profile, experience, technology, etc.), `text` (content), and `metadata` (structured fields).
- **NormalizerOutput**: Result of normalizer processing — filtered facts, removed count, rules applied, rendered text.
- **TECH_ABBREVIATIONS**: Bidirectional mapping of technology names to their abbreviations/translations, used for cross-language keyword matching.

## Assumptions

- The profile document type (`profile`) is the primary source of high-level competency information and should be treated as a valid evidence source for technology usage queries.
- The `focus_area` document type contains detailed bullet-point descriptions of skill areas that are directly relevant to technology usage questions.
- The `tech_focus` document type contains structured technology competency data (category label + tool/framework tags) that is directly relevant to technology usage queries. Example: "ML и CV — PyTorch, Ultralytics, YOLO, Detectron2, OpenCV, NumPy, Pandas".
- The existing content-level keyword filtering (Rule 2b) with `_filter_fact_bullets()` and `_build_content_keywords()` is sufficient for preventing false positives from profile/focus_area/tech_focus facts — no new filtering mechanism is needed.
- The `TECH_ABBREVIATIONS` mapping is the correct extension point for handling concept-level terms that don't exist as Technology entities.
- The normalizer's zero-result safety fallback is a general improvement that benefits all intents, not just technology_usage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The query "какой опыт с ИИ агентами" returns a substantive answer that mentions AI agents in the context of the developer's current work — instead of "нет информации".
- **SC-002**: The normalizer retains profile-type facts that contain the queried technology keyword in their text content — the type filter does not drop them, and Rule 2b content matching confirms the keyword presence.
- **SC-003**: The normalizer does NOT introduce false positives: profile facts that do NOT mention the queried technology are still correctly filtered out.
- **SC-004**: All existing tests continue to pass without modification (no regressions).
- **SC-005**: Queries about other concept-level skills (RAG, Computer Vision, LLM) also return correct answers that include profile/focus area/tech_focus information alongside structured technology data.
- **SC-006**: The query "какой опыт с машинным обучением" returns an answer that includes specific ML tools (PyTorch, YOLO, Detectron2, etc.) from the tech_focus document — regardless of which intent the planner assigns.

## Clarifications

### Session 2026-02-28

- Q: Does the ML case ("какой опыт с машинным обучением" vs "какой опыт с ML") share the same root cause as the AI agents case? → A: Yes, same root cause — the normalizer's `technology_usage_filter` is too restrictive. The ML case currently works only because the planner routes it to `experience_summary` intent (which uses a less restrictive filter), not because the normalizer handles it correctly. If the planner ever classifies ML queries as `technology_usage`, the `tech_focus` document would be dropped.
- Q: Is the `tech_focus` document type missing from FR-001? → A: Yes, `tech_focus` was not listed in FR-001. It has been added alongside `profile` and `focus_area`. The `tech_focus` type contains structured technology competency data (e.g., "ML и CV: PyTorch, YOLO, Detectron2, OpenCV, NumPy, Pandas") that is directly relevant to technology usage queries.
- Q: Should `stat` and `work_approach` types also be added to the allowed types? → A: No. `stat` type documents (e.g., "5+ лет, Python/.NET, Backend, ML") are too generic and would add noise. `work_approach` documents describe methodology, not technology usage. These are correctly excluded by the type filter.

### Session 2026-02-28 (Regression Analysis)

- Q: Can the expanded type filter (FR-001/FR-005) introduce false positives for specific technology queries? → A: No. Rule 2b content-level filtering acts as a second guard — facts whose text doesn't contain the queried technology keyword are rejected regardless of type. Verified against normalizer code: `_filter_fact_bullets` returns `None` for non-bullet facts that don't match keywords.
- Q: Does the deterministic `_answer_technology_usage` path break with new fact types (profile, focus_area, tech_focus)? → A: No. The method expects metadata with `technology`/`project` keys (graph facts) or `name`/`project_names` (hybrid facts). New fact types lack these fields and are safely ignored. If deterministic path returns None, the LLM path takes over with additional useful context.
- Q: Are other intents (experience_summary, technology_overview, etc.) affected by the changes? → A: No. The type filter is gated by `if intent_str == "technology_usage"` (line 108). Rules 1 and 3 are not modified. No other pipeline components are changed.
- Q: Could the zero-result fallback (FR-003) mask legitimate "no data" cases? → A: No. FR-003 only triggers when type-filtering removes ALL facts. With expanded types, this scenario is even less likely. When the portfolio genuinely has no data about a topic, hybrid search returns 0 facts upstream — the normalizer never runs on empty input.
- Q: Is there a risk from `entity_names=None` with expanded types (Rule 2b skipped)? → A: Theoretical risk only. For `technology_usage` intent, the planner always generates a technology entity (required for graph query). `entity_names` is populated from `plan.entities` in `rag_tool.py` (lines 288-292). The None case is unreachable in practice.
