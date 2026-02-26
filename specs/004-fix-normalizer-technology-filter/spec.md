# Feature Specification: Fix Technology Query Bugs

**Feature Branch**: `004-fix-normalizer-technology-filter`
**Created**: 2026-02-26
**Status**: Draft
**Input**: Two related bugs in technology query pipeline: (1) Normalizer technology_usage_filter drops experience/experience_project docs causing inconsistent answers; (2) graph_query_tool for technology_overview truncates to ~12 alphabetically-first technologies, omitting Python/LangChain/AI stack entirely.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent answers for technology usage questions (Priority: P1)

A user asks the portfolio agent about experience with a specific technology domain (e.g., "какой опыт с компьютерным зрением"). The agent MUST consistently find and return relevant information regardless of how the question is phrased, as long as the information exists in the portfolio data.

**Why this priority**: The agent gives contradictory answers to semantically equivalent questions, which undermines trust. A user asking "какой опыт с компьютерным зрением" gets "no experience found", but asking "где использовал компьютерное зрение" correctly returns the t2/Aston CV project.

**Independent Test**: Ask multiple paraphrases of the same technology usage question and verify all return consistent, correct answers.

**Acceptance Scenarios**:

1. **Given** the portfolio contains experience with computer vision (Aston/t2 project with Detectron2, Ultralytics, YOLO), **When** user asks "какой опыт с компьютерным зрением", **Then** the agent returns information about CV experience at t2 including specific technologies used.
2. **Given** the portfolio contains experience with computer vision, **When** user asks "где использовал компьютерное зрение", **Then** the agent returns the same t2/Aston CV project information (consistent with scenario 1).
3. **Given** the portfolio contains experience with a technology mentioned only in `experience` or `experience_project` documents, **When** user asks about that technology with intent `technology_usage`, **Then** the agent finds and returns that information.

---

### User Story 2 - Normalizer preserves experience documents for technology_usage intent (Priority: P1)

When the RAG pipeline processes a `technology_usage` intent query, the normalizer MUST NOT discard `experience` and `experience_project` documents that contain relevant technology usage information.

**Why this priority**: Root cause of bug 1. The `technology_usage_filter` only keeps document types `("technology_usage", "technology", "project")`, silently dropping `experience` and `experience_project` docs where technology usage is described in achievements text.

**Independent Test**: Pass facts including `experience` type documents through the normalizer with `technology_usage` intent and verify they are retained.

**Acceptance Scenarios**:

1. **Given** the normalizer receives facts including an `experience` document mentioning "компьютерное зрение" in achievements, **When** normalizer applies `technology_usage_filter`, **Then** the `experience` document is retained.
2. **Given** the normalizer receives facts including an `experience_project` document with technology-related achievements, **When** normalizer applies `technology_usage_filter`, **Then** the `experience_project` document is retained.
3. **Given** the normalizer receives facts with only irrelevant types (e.g., `stat`, `profile`) for a `technology_usage` query, **When** normalizer applies `technology_usage_filter`, **Then** those irrelevant documents are still correctly filtered out.

---

### User Story 3 - Complete technology list for technology_overview queries (Priority: P1)

A user asks "какими технологиями владеет Дмитрий" and expects to receive a comprehensive, representative list of technologies including Python, LangChain, FastAPI, LangGraph — i.e., the primary modern AI/Python stack. Currently the agent returns only ~12 alphabetically-first technologies (all .NET/C# legacy stack) and omits the core competencies entirely.

**Why this priority**: This is the most visible bug — a recruiter or visitor asking about technology skills gets a completely wrong impression. The agent presents Dmitry as a .NET developer when his primary focus is Python/AI/LLM.

**Independent Test**: Ask "какими технологиями владеет Дмитрий" and verify that Python, LangChain, FastAPI, and at least one other modern AI framework appear in the response.

**Acceptance Scenarios**:

1. **Given** the portfolio contains 20+ technologies across all projects, **When** user asks "какими технологиями владеет Дмитрий", **Then** the response includes Python, LangChain, FastAPI, and other primary AI/Python stack technologies.
2. **Given** 20 technologies exist in the graph, **When** graph_query_tool is called for `technology_overview`, **Then** all 20 technologies are returned to the executor (not truncated to 12).
3. **Given** the full technology list is returned, **When** the response is rendered, **Then** technologies are presented in a meaningful order that reflects current relevance (not alphabetical, which buries the primary stack).

---

### User Story 4 - No regression in existing normalizer behavior (Priority: P2)

All other normalizer rules and intents continue to function correctly after the fix.

**Why this priority**: Ensure the fix is surgical and does not break existing behavior for other intents.

**Independent Test**: Run the existing test suite and verify all normalizer-related tests pass.

**Acceptance Scenarios**:

1. **Given** a query with intent `contacts`, **When** the normalizer processes results, **Then** behavior is unchanged.
2. **Given** a query with intent `project_details`, **When** the normalizer processes results, **Then** behavior is unchanged.

---

### Edge Cases

- What happens when the only relevant document is an `experience_project` type and no `project` or `technology` type documents exist for the queried technology? The system should still return the `experience_project` information.
- What happens when hybrid search does not retrieve the relevant `experience` document at all? Secondary issue (search quality) outside this fix scope, but the normalizer must not worsen it.
- What if the portfolio grows to 50+ technologies — will the technology_overview response become too long? The fix must ensure completeness without producing an unusable wall of text. Grouping by category is the mitigation.
- What happens when graph_query_tool is called with no entity filter for `technology_overview` — should it return technologies from ALL projects or only featured/active ones? (Covered under FR-006.)

## Requirements *(mandatory)*

### Functional Requirements

**Bug 1 — Normalizer filter:**

- **FR-001**: The normalizer's `technology_usage_filter` rule MUST include `experience` and `experience_project` document types in its whitelist alongside existing types (`technology_usage`, `technology`, `project`).
- **FR-002**: When the normalizer processes facts for `technology_usage` intent, it MUST retain documents of types: `technology`, `technology_usage`, `project`, `experience`, and `experience_project`.
- **FR-003**: The normalizer MUST continue to filter out clearly irrelevant document types (e.g., `stat`, `profile`, `focus_area`, `work_approach`, `catalog`) for `technology_usage` intent when relevant documents of allowed types exist.
- **FR-004**: The existing fallback behavior (if no documents match the whitelist, keep all documents) MUST be preserved.
- **FR-005**: The normalizer log output MUST continue to report the `technology_usage_filter` rule as applied when filtering occurs.

**Bug 2 — Graph query truncation for technology_overview:**

- **FR-006**: The graph query for `technology_overview` intent MUST return ALL technologies present in the knowledge graph — not truncated by an alphabetical-order limit. The current behavior of returning only the first ~12 alphabetically MUST be fixed.
- **FR-007**: Technologies returned for `technology_overview` MUST be ordered by **recency** — technologies from more recent projects appear first. Technologies from projects dated 2024-2025 (Python, LangChain, LangGraph, FastAPI, etc.) MUST precede technologies from older projects (2021-2023: .NET, C#, ADO.NET). Within the same recency tier, ordering by category is acceptable.
- **FR-008**: The item limit for `technology_overview` queries MUST be set to **20–25** to match the actual technology count in the portfolio (~20 currently) with slight headroom for growth. A hard cap below 20 MUST NOT be applied.
- **FR-009**: Plan cache MUST be cleared as a mandatory deployment step after applying the fix. Without cache clearing, previously cached plans with the old `max_items` value will continue to truncate technology results. This step MUST be documented in the deployment quickstart.

### Key Entities

- **FactItem**: A retrieved document with `type` field (profile, experience, experience_project, project, technology, stat, etc.). The normalizer filters facts by type based on query intent.
- **NormalizerOutput**: Result of normalization containing filtered facts list and applied rules.
- **TechnologyNode**: A node in the knowledge graph representing a technology, with fields: name, slug, category, and linked project_ids.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "какой опыт с компьютерным зрением" and "где использовал компьютерное зрение" both return the t2/Aston CV experience with Detectron2/Ultralytics/YOLO.
- **SC-002**: The normalizer retains all `experience` and `experience_project` documents for `technology_usage` intent queries.
- **SC-003**: No regression in existing normalizer behavior for non-`technology_usage` intents (all existing tests pass).
- **SC-004**: The normalizer fix is minimal and surgical — only the whitelist in `technology_usage_filter` is modified.
- **SC-005**: "какими технологиями владеет Дмитрий" returns a response that includes Python, LangChain, FastAPI, and at least 5 other primary AI/Python stack technologies.
- **SC-006**: Technologies in the `technology_overview` response are ordered by recency — technologies from 2024-2025 projects (Python, LangChain, FastAPI, LangGraph) appear before technologies from 2021-2023 projects (.NET, C#, ADO.NET). The response includes ALL technologies from the portfolio (~20+), not a truncated alphabetical subset.
- **SC-007**: After deployment and plan cache clearing, subsequent requests for "какими технологиями владеет Дмитрий" return the complete, recency-ordered technology list.

### Assumptions

- The hybrid search pipeline correctly retrieves relevant `experience` and `experience_project` documents for technology usage queries in most cases. This spec addresses the normalizer silently discarding them after retrieval.
- The answer LLM can correctly identify technology usage information from `experience`/`experience_project` document content when it is present in the rendered facts.
- "Computer Vision" is not present as a node in the knowledge graph (confirmed by logs: `Entity key 'computer-vision' not found in graph`). This is expected and not part of this fix.
- The knowledge graph contains ~20+ technology nodes. The `technology_overview` fix must return all of them without imposing an arbitrary alphabetical-order cutoff.

## Clarifications

### Session 2026-02-26

- Q: Should this spec expand to cover the `technology_overview` graph query truncation bug, or should that be a separate spec 005? → A: Expand spec 004 to cover both bugs in one PR.
- Q: How should technologies be ordered for `technology_overview`, and what item limit is optimal? → A: Recency ordering (most recent projects first) + limit set to 20–25 (matches current ~20 technologies with headroom; 16 would truncate).
- Q: Should plan cache clearing be a mandatory deployment step? → A: Yes (Option A) — mandatory manual step after deploy, document in quickstart.
