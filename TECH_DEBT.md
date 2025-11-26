# Tech Debt Log

This file tracks intentional technical debt taken on to keep development moving.
Each entry should include context and a rough plan to address it.

## Entries

### 1. Durable HTTP starter and orchestrator use `*_impl` wrappers
- **Date**: 2025-11-24
- **Area**: `function_app.py`
- **Decision**:
  - Introduced `http_start_impl` (alias of `_http_start_impl`) so unit tests can call the HTTP starter logic directly without relying on Durable decorators.
  - Introduced `main_orch_impl` so tests can exercise orchestrator logic with a dummy context instead of the real Durable runtime.
- **Reasoning**:
  - Durable Functions v2 decorators (`DFApp.route`, `DFApp.orchestration_trigger`, etc.) can obscure the underlying callable and complicate unit testing.
  - The `*_impl` pattern lets us keep a clean separation between binding-facing entry points and plain Python logic while we focus on behavior and tests.
- **Impact / Risk**:
  - Slight duplication of entry points (decorated wrapper + implementation) and an extra concept for future maintainers to understand.
  - If not documented, future refactors might accidentally bypass the `*_impl` functions or diverge behavior.
- **Planned resolution**:
  - Once the pipeline stabilizes and integration tests are in place, re-evaluate whether we can:
    - Rely on the decorated functions directly in tests (if Durable APIs improve), or
    - Clearly enshrine the `*_impl` pattern as a project convention in docs.

### 2. Future stubbed activity implementations (e.g., `pdf_split_impl`)
- **Date**: 2025-11-24
- **Area**: Activity functions (planned)
- **Decision**:
  - We plan to introduce stubbed implementations such as `pdf_split_impl` that return deterministic fake data (e.g., a small set of pages) before wiring in real PDF parsing, storage, and error handling.
- **Reasoning**:
  - Allows us to develop and test orchestration and control flow end-to-end without being blocked by PDF parsing and storage concerns.
- **Impact / Risk**:
  - Behavior in tests and early environments will not reflect real-world document structures or edge cases.
  - Risk of forgetting to replace stubs with full implementations before production hardening.
- **Planned resolution**:
  - Track each stubbed `*_impl` in this file.
  - For each, create a checklist item in `docs/implementation-checklist.md` to replace stub logic with real behavior and add more exhaustive tests (including error paths).
