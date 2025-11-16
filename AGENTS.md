# Repository Guidelines

## Project Structure & Module Organization
Core automation code lives in `autokitteh-source/`, with the Go control plane in `cmd/` and durable Python runtimes under `runtimes/pythonrt/`. The Codex CLI, SDKs, and Rust workspace live in `codex-source/` (`codex-cli/`, `codex-rs/`, `sdk/`). Specialized Python agents, orchestration scripts, and reusable skills are kept in `intelligent-agents/`, `skills/`, and `workflows/`. Model Context Protocol servers sit under `mcp-servers/` (mix of Python and Node). Operational tooling (Grafana dashboards, alerts, probes) is under `monitoring/`. Integration tests and scenario harnesses reside beside the root (`test_rag_integration.py`, `test_quality_gates_integration.py`, `test_diverse_workflows.py`) plus module-specific test folders. Architecture docs, runbooks, and status reports are in `docs/` and the top-level `*_STATUS*.md` files. Reuse `docs/images/` for diagrams and `assets/` folders inside each package for binary data.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate && pip install -r intelligent-agents/requirements.txt`: prepare the shared virtualenv for the Python agents and scripts.
- `python demo_agi_workflow.py --config agi_config.json`: run the reference AGI workflow end-to-end; fails fast if orchestrator wiring is broken.
- `cd autokitteh-source && make ak && go test ./...`: build the automation server binary and run Go unit tests.
- `cd codex-source && pnpm install && pnpm format && cargo fmt && cargo clippy && cargo test`: install JavaScript tooling, enforce formatting, and run the Rust workspace checks used by CI.
- `pytest -q test_rag_integration.py test_quality_gates_integration.py`: validate RAG + quality-gate flows before opening a PR.

## Coding Style & Naming Conventions
Use 4-space indentation and type hints for Python; lint with `ruff check` and `ruff format` (see `autokitteh-source/runtimes/pythonrt/pyproject.toml`). Follow snake_case for modules/files, CamelCase for classes, and ALL_CAPS for environment constants. Go code must pass `gofumpt` and `golangci-lint` (AutoKitteh Makefile enforces both). Rust code uses `cargo fmt` + `cargo clippy --tests`. JavaScript/TypeScript and Markdown formatting is handled by `pnpm format` (Prettier). Keep assets in lowercase directories and mirror source package names when adding new components.

## Testing Guidelines
Unit tests live alongside their modules (e.g., `autokitteh-source/.../_test.go`, `codex-source/codex-rs/**/tests`). Name Python tests `test_*` so `pytest` auto-discovers them. Prefer targeted module tests plus the scenario files in repo root to safeguard cross-agent workflows. Integration work that touches MCP servers should include smoke steps via `scripts/test_sandbox.py` or `test_diverse_workflows.py`. Document new test entry points in the relevant README and capture expected artifacts under `monitoring/` if dashboards change.

## Commit & Pull Request Guidelines
The repo uses Conventional Commits so tooling such as `codex-source/cliff.toml` can group changes; start messages with `feat:`, `fix:`, `chore:`, etc., and scope when helpful (`feat(rag): ...`). Keep commits focused (doc-only, infra-only, code changes separately). PRs must include: summary of intent, runnable commands (`python demo_agi_workflow.py`, `pytest ...`), linked issue/task IDs when available, and screenshots or log excerpts for monitoring/UI tweaks. Update any affected docs (`docs/`, status reports) and mention configuration changes explicitly.

## Security & Configuration Tips
Secrets live in `.env`, `config/config.env`, and service-specific `.env.*` files—never commit actual credentials. Reference shared settings through `agi_config.json` and `config/` readers instead of hardcoding paths. When working on MCP servers or cloud connectors, validate that test data stays under `sandbox/` or `n8n-data/` to avoid leaking production payloads. Rotate API keys used in local testing and scrub them from logs before attaching to issues.
