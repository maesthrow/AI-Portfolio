# Feature Specification: Fix Project List Query

**Feature Branch**: `002-fix-project-list-query`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Fix systemic issue where AI agent cannot correctly answer project listing questions with filters (personal/commercial projects, projects by technology, by domain). Multiple pipeline layers fail: planner generates wrong intents, graph has no project listing capability, search returns irrelevant results, normalizer doesn't filter, answer dumps all facts."

## Problem Statement

When a user asks the AI agent questions about listing projects with filters, the system fails at multiple layers:

**Observed failures** (from production logs):

1. "Какие есть личные проекты" — agent returned only 2 of 3 personal projects, hallucinated one (HyperKeeper appeared without evidence), missed ReAct-Agent entirely
2. "Какие есть проекты с LLM" — agent included F3 TAIL (C#/.NET) and СКИО (C#/.NET) as "LLM projects" despite neither having any LLM-related technologies

**Root cause analysis** identified failures at every pipeline layer:

- **Query planner**: Generates invalid intent+entity combinations (e.g., `project_details` + `person:dmitry` instead of a proper project listing intent)
- **Knowledge graph**: No query handler exists for "list all projects of a person with optional filters" — the closest handler (`_project_details_query`) only finds a single project by slug
- **Semantic search**: Returns irrelevant documents because "личные проекты" or "проекты LLM" don't semantically match individual project descriptions well
- **Fact normalizer**: Passes all facts through without filtering by requested technology/type
- **Answer generator**: Deterministic renderer dumps all facts as bullets without relevance filtering

## User Scenarios & Testing *(mandatory)*

### User Story 1 - List All Personal Projects (Priority: P1)

A user asks the agent "Какие есть личные проекты?" and expects a complete list of all personal (non-commercial) projects with their brief descriptions.

**Why this priority**: This is the most common project listing question and the original bug report. Currently returns incomplete/hallucinated results.

**Independent Test**: Can be tested by asking the agent "какие есть личные проекты" and verifying that all personal projects (those without a company affiliation) are returned, and no commercial projects are included.

**Acceptance Scenarios**:

1. **Given** the knowledge graph contains personal projects (AI-Portfolio, HyperKeeper, ReAct-Agent), **When** user asks "какие есть личные проекты", **Then** all three personal projects are listed with names and brief descriptions, and no commercial projects appear
2. **Given** the knowledge graph contains personal projects, **When** user asks "расскажи о своих проектах" (ambiguous — could mean personal), **Then** the agent lists all projects (both personal and commercial) grouped logically
3. **Given** the knowledge graph contains personal projects, **When** user asks "personal projects", **Then** the same result as scenario 1 is returned (language-agnostic)

---

### User Story 2 - List Projects by Technology (Priority: P1)

A user asks "Какие есть проекты с LLM?" and expects only projects that actually use LLM-related technologies.

**Why this priority**: Technology-filtered queries are the second most common project listing pattern. Currently returns irrelevant projects (F3 TAIL, СКИО listed as "LLM projects").

**Independent Test**: Can be tested by asking "какие проекты с LLM" and verifying only projects with LLM-related technologies (LangChain, LangGraph, vLLM, GigaChat, etc.) are returned.

**Acceptance Scenarios**:

1. **Given** the knowledge graph has projects with various technologies, **When** user asks "какие проекты с LLM", **Then** only projects using LLM-related technologies are returned (t2, AI-Portfolio, HyperKeeper, ReAct-Agent) and projects without LLM (F3 TAIL, СКИО) are excluded
2. **Given** the knowledge graph has projects, **When** user asks "проекты с PostgreSQL", **Then** only projects that use PostgreSQL are listed
3. **Given** the knowledge graph has projects, **When** user asks "где использовался Docker", **Then** projects with Docker in their technology list are returned

---

### User Story 3 - List Commercial Projects (Priority: P2)

A user asks "Какие есть коммерческие проекты?" and expects only projects done for companies.

**Why this priority**: Less common than personal/tech queries but completes the set of project type filters.

**Independent Test**: Can be tested by asking "коммерческие проекты" and verifying only company-affiliated projects appear.

**Acceptance Scenarios**:

1. **Given** the knowledge graph has commercial projects (t2, АЛОР БРОКЕР, F3 TAIL, СКИО), **When** user asks "какие есть коммерческие проекты", **Then** all commercial projects are listed with company names, and no personal projects appear
2. **Given** the knowledge graph has commercial projects, **When** user asks "рабочие проекты", **Then** commercial projects are returned (synonym handling)

---

### User Story 4 - List All Projects (Priority: P2)

A user asks "Какие есть проекты?" without any filter and expects a complete overview of all projects.

**Why this priority**: General listing should work reliably as the base case for all filtered variants.

**Independent Test**: Can be tested by asking "расскажи о проектах" and verifying all projects (personal + commercial) are returned.

**Acceptance Scenarios**:

1. **Given** the knowledge graph has all projects, **When** user asks "какие есть проекты", **Then** all projects are listed, grouped by type (personal/commercial) or chronologically
2. **Given** the knowledge graph has all projects, **When** user asks "over how many projects has Dmitry worked", **Then** a count and list of all projects is provided

---

### Edge Cases

- What happens when user asks about a technology category that no project uses (e.g., "проекты с Kotlin")? — Agent should respond that no projects with that technology were found
- What happens when user asks about projects with an ambiguous term (e.g., "AI-проекты") that is a domain, not a specific technology? — Agent should match projects by domain or by related technology categories (ml_framework, concept:LLM, concept:RAG)
- What happens when user combines filters (e.g., "личные проекты с LLM")? — Agent should apply both filters (personal + LLM technology)
- What happens when the planner generates an invalid intent+entity combination? — The system should gracefully handle it rather than returning 0 results

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to list all projects belonging to a person, returning complete results (no missing projects)
- **FR-002**: The system MUST support filtering projects by kind: "personal" (no company affiliation) vs "commercial" (company-affiliated)
- **FR-003**: The system MUST support filtering projects by technology name (exact match against the project's technology list)
- **FR-004**: The system MUST support filtering projects by technology category (e.g., "ml_framework" matches all projects using any technology in that category: LangChain, LangGraph, vLLM, etc.)
- **FR-005**: The system MUST support filtering projects by domain (e.g., "Web AI", "Telecom", "Retail")
- **FR-006**: The system MUST return project details including: name, description, technologies, period, company name (if commercial), domain, repo/demo URLs
- **FR-007**: The query planner MUST never generate `project_details` intent with a person entity — project listing must use a dedicated listing mechanism
- **FR-008**: The query planner MUST correctly route project listing questions to the appropriate query handler based on the presence/absence of filters
- **FR-009**: When no projects match the applied filters, the system MUST respond with a clear "no projects found" message rather than returning unrelated results
- **FR-010**: The answer generator MUST NOT include facts that are irrelevant to the user's filter criteria (e.g., no C#/.NET projects in response to "projects with LLM")

### Key Entities

- **Project**: A software project with attributes: name, slug, description, technologies (list), domain, period, company_name (null for personal), kind (personal/commercial), repo_url, demo_url
- **Technology**: A named technology with a category classification (language, framework, ml_framework, database, concept, tool, etc.)
- **Technology Category**: A grouping of technologies (e.g., ml_framework includes LangChain, LangGraph, vLLM, PyTorch)
- **Person**: The portfolio owner, connected to projects via "created" relationships

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When asked "какие есть личные проекты", the agent returns 100% of personal projects (currently returns 66% — 2 of 3) with zero hallucinated projects
- **SC-002**: When asked "какие есть проекты с LLM", the agent returns only projects with LLM-related technologies — zero false positives (currently 2 false positives: F3 TAIL, СКИО)
- **SC-003**: When asked "коммерческие проекты", the agent returns only company-affiliated projects with zero personal projects mixed in
- **SC-004**: When asked "какие есть проекты", the agent returns a complete list of all projects — 100% recall
- **SC-005**: All project listing queries complete within the same time budget as other agent queries (no noticeable latency regression)
- **SC-006**: Agent responses to project listing questions are grounded exclusively in retrieved evidence — zero hallucinated projects or technologies

## Assumptions

- The knowledge graph is the authoritative source for structured project data (names, technologies, company affiliation, domain)
- Technology category mappings are maintained in the existing `TECHNOLOGIES_WITH_CATEGORIES` dictionary and are considered complete for current projects
- The portfolio contains a manageable number of projects (currently 7) so full listing without pagination is acceptable
- "Personal project" is defined as a project where `company_name` is null/empty; all other projects are "commercial"
- Technology filtering by category should be inclusive: asking about "LLM" should match projects using LangChain, LangGraph, vLLM, GigaChat, etc. (technologies in the ml_framework category and LLM/RAG concepts)
