# Agent Communication MCP Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build an authenticated FastMCP service that lets Stephen's server/dev/desktop agents communicate, discover capabilities, exchange artifacts, and access project-scoped filesystem context through launcher-project-registry.

**Architecture:** One FastMCP HTTP/StreamableHTTP service first. It exposes MCP tools for project/context lookup, scoped artifact/file operations, agent cards, and a task mailbox. Official A2A compatibility is deferred until the MCP-native mailbox proves useful.

**Tech Stack:** Python 3.11+, FastMCP, pytest, httpx, SQLite or JSON persistence, launcher-project-registry adapter.

---

## Phase 0: Research and repo governance

### Task 0.1: Confirm official auth/A2A docs

**Objective:** Capture primary-source decisions before coding.

**Files:**
- Modify: `research/RESEARCH.md`

**Steps:**
1. Re-check MCP authorization, MCP roots, MCP transports, and A2A Agent Card/task lifecycle docs.
2. Add direct citations/quotes to `research/RESEARCH.md`.
3. Keep article MCP brief as secondary/practitioner evidence only.

**Verification:** `grep -n "Official/primary" research/RESEARCH.md` shows the primary-doc section.

### Task 0.2: Register project in launcher registry

**Objective:** Make the project discoverable to existing agents.

**Files:**
- External: `/home/stephen/projects/launcher-project-registry/registry.json` via `registry_ops.upsert_project()` only.

**Steps:**
1. Import `upsert_project` from launcher registry.
2. Upsert slug `agent-communication-mcp` with path `/home/stephen/projects/agent-communication-mcp`.
3. Include tech stack `python`, `fastmcp`, `mcp`, `a2a`, `sqlite`.

**Verification:** launcher `registry.json` contains the slug and `has_context_md` is true after scanner/sync.

## Phase 1: Skeleton FastMCP server

### Task 1.1: Create Python package scaffold

**Objective:** Add package, app entrypoint, and tests.

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_communication_mcp/server.py`
- Create: `src/agent_communication_mcp/__init__.py`
- Create: `tests/test_import.py`

**Steps:**
1. Add dependencies: `fastmcp`, `pydantic`, `httpx`, `pytest`.
2. Create `mcp = FastMCP("Agent Communication MCP")`.
3. Add `health()` tool returning name/version/status.
4. Test import and health tool function.

**Verification:** `uv run pytest -q` passes.

### Task 1.2: Add local HTTP run script

**Objective:** Run service locally before gateway integration.

**Files:**
- Modify: `src/agent_communication_mcp/server.py`
- Create: `scripts/run_http.py`

**Verification:** `uv run python scripts/run_http.py` starts a StreamableHTTP server on a free launcher-approved port.

## Phase 2: Auth and authorization scopes

### Task 2.1: Bearer token authentication

**Objective:** Reject unauthenticated HTTP requests.

**Files:**
- Create: `src/agent_communication_mcp/auth.py`
- Modify: `src/agent_communication_mcp/server.py`
- Create: `tests/test_auth.py`

**Steps:**
1. Read allowed tokens from env var or config file outside repo.
2. Map tokens to agent identities and scopes.
3. Add tests for missing/invalid/valid bearer token.

**Verification:** HTTP probe without token fails; with token succeeds.

### Task 2.2: Scope model

**Objective:** Define exact read/write capabilities per agent.

**Files:**
- Create: `src/agent_communication_mcp/scopes.py`
- Create: `tests/test_scopes.py`

**Scopes:**
- `registry:read`
- `project_context:read`
- `artifact:read`
- `artifact:write`
- `mailbox:read`
- `mailbox:write`
- `task:submit`
- `task:update`
- `fs:read:<scope>`
- `fs:write:<scope>`

**Verification:** denied scope raises explicit authorization error.

## Phase 3: Launcher registry adapter

### Task 3.1: Read launcher registry safely

**Objective:** Query project metadata without duplicating registry logic.

**Files:**
- Create: `src/agent_communication_mcp/launcher_registry.py`
- Create: `tests/test_launcher_registry.py`

**Steps:**
1. Default registry path: `/home/stephen/projects/launcher-project-registry/registry.json`.
2. Implement `list_projects`, `get_project`, `get_project_context`.
3. Resolve project paths with `Path.resolve()`.

**Verification:** Tests use a temp registry fixture and prove no direct writes.

### Task 3.2: Expose MCP tools

**Objective:** Add registry tools.

**Tools:**
- `list_projects(filter_query="")`
- `get_project_context(slug)`
- `resolve_project_workspace(slug)`

**Verification:** FastMCP list/call shows each tool and returns fixture data.

## Phase 4: Scoped filesystem/artifact tools

### Task 4.1: Path sandboxing

**Objective:** Prevent path traversal and broad disk reads.

**Files:**
- Create: `src/agent_communication_mcp/path_sandbox.py`
- Create: `tests/test_path_sandbox.py`

**Steps:**
1. Resolve all paths against approved project roots or agent artifact roots.
2. Reject symlink/path traversal outside allowed roots.
3. Cap read sizes and directory listing counts.

**Verification:** tests for `../`, symlink escape, absolute unauthorized path all fail closed.

### Task 4.2: Artifact store

**Objective:** Exchange files/content without arbitrary write access.

**Tools:**
- `publish_artifact(task_id, name, content|source_path)`
- `list_artifacts(task_id)`
- `read_artifact(artifact_id)`

**Verification:** artifact writes land under `.agent-artifacts/` only.

## Phase 5: A2A-shaped agent cards and mailbox

### Task 5.1: Agent cards

**Objective:** Publish capabilities for `server-agent`, `dev-agent`, and `desktop-agent`.

**Files:**
- Create: `src/agent_communication_mcp/agent_cards.py`
- Create: `agent-cards/server-agent.json`
- Create: `agent-cards/dev-agent.json`
- Create: `agent-cards/desktop-agent.json`

**Tools:**
- `list_agents()`
- `get_agent_card(agent_id)`

**Verification:** each card includes id, description, capabilities, endpoint, auth scheme, scopes.

### Task 5.2: Mailbox/task lifecycle

**Objective:** Add durable handoff primitives.

**Files:**
- Create: `src/agent_communication_mcp/tasks.py`
- Create: `src/agent_communication_mcp/storage.py`
- Create: `tests/test_tasks.py`

**Tools:**
- `drop_agent_message(agent_id, subject, body, artifacts=[])`
- `list_agent_inbox(agent_id)`
- `submit_task(agent_id, title, instructions, project_slug=None, artifacts=[])`
- `get_task(task_id)`
- `append_task_event(task_id, event)`

**Task states:** `submitted`, `working`, `input_required`, `completed`, `failed`, `cancelled`.

**Verification:** task lifecycle tests cover submit → working → completed and authorization checks.

## Phase 6: Gateway/launcher integration

### Task 6.1: Register service metadata

**Objective:** Upsert runtime metadata in launcher registry.

**Fields:**
- `transport: http`
- `ports: [chosen_port]`
- `url: http://127.0.0.1:<port>/mcp`
- `tags: ["mcp", "a2a", "agent-communication", "filesystem"]`

**Verification:** launcher `get_project_info` returns the project.

### Task 6.2: Hermes MCP config path

**Objective:** Document how to connect Hermes after service is running.

**Files:**
- Create: `docs/HERMES_CONNECT.md`

**Verification:** include `hermes config set mcp_servers.agent_communication.url ...` commands and note restart requirement.

## Phase 7: Security review gate

### Task 7.1: Abuse-case tests

**Objective:** Prove the first release fails closed.

**Tests:**
- unauthenticated calls
- wrong agent accessing inbox
- path traversal
- unauthorized project path
- oversized artifact
- missing audit event

**Verification:** `uv run pytest -q` passes.

### Task 7.2: Release decision

**Objective:** Decide whether to add official A2A protocol server next.

**Criteria:**
- mailbox used by at least two agent identities
- task lifecycle useful in real handoff
- no scope/audit blockers
- endpoint stable enough to expose beyond localhost
