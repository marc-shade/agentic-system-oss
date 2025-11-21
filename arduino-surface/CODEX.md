# CODEX.md

Guidance for OpenAI Codex contributors working inside the Arduino Surface repository. This mirrors the expectations that are already documented for Claude Code in `CLAUDE.md` and should be considered authoritative for Codex operations.

## Project Overview

- **Purpose**: Provide a hardware control surface (LCD, RGB LED, servo, buzzer, sensors, buttons) that bridges agent workflows to the physical world.
- **Stack**:
  - `firmware/agentic_surface/agentic_surface.ino` — Arduino sketch exposing a text command protocol at 115200 baud.
  - `bridge/surface_bridge.py` — PySerial wrapper and event loop.
  - `daemons/*.py` — background services for status, Ember sync, and telemetry.
  - `mcp-server/arduino_surface_mcp.py` — JSON-RPC MCP server used by desktop agents.
  - `examples/` + `scripts/` — smoke tests and daemon lifecycle helpers in `/tmp/arduino_daemon.{pid,log}`.

## Operating Principles

1. **Preserve hardware stability** — do not change the serial protocol without touching firmware, bridge, and docs together.
2. **Minimize side-effects on import** — Python modules should only wire up serial connections inside explicit functions/classes.
3. **Respect existing scripts** — start/stop daemons via `scripts/*.sh` and leave PID/log cleanup logic intact.
4. **Document manual verification** — every hardware-facing change needs reproducible steps in PR descriptions.

## Environment & Tooling

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
arduino-cli compile --fqbn arduino:avr:uno firmware/agentic_surface
```

- Agentic stack workflow: `bash scripts/start_agentic_stack.sh /dev/tty.usbmodemXXXX [daemon.py]` to launch the enhanced daemon plus Ember API; check via `scripts/daemon_status.sh` and stop with `scripts/stop_agentic_stack.sh`. Use `scripts/start_daemon.sh` directly only for advanced/experimental daemons.
- MCP bridge: run `python3 mcp-server/arduino_surface_mcp.py` after the daemon reports healthy.
- Ember helpers: `python3 scripts/feed_ember.py` and `python3 examples/human_in_loop_example.py`.

## Coding Style Expectations

- **Python**: PEP 8, four-space indents, snake_case functions, UpperCamelCase classes, type hints on new entry points.
- **Arduino**: two-space indents, ALL_CAPS pin constants, and small helpers that respect UNO constraints.
- **Shell**: POSIX-compatible, actionable ✓/✗ status output, defensive handling of stale PID/log files.

## Testing Guidance

- Run `arduino-cli compile` for every firmware change; verify the `"status":"ready"` serial handshake before completing a feature.
- Use the interactive examples (`python3 examples/arc2_puzzle_interface.py`, `human_in_loop_example.py`) as smoke tests with hardware.
- Add `pytest` cases in `tests/test_*.py` when expanding Python logic; mock or fake serial interfaces where feasible.

## Commit & Review Process

- Follow Conventional Commits (`feat:`, `fix:`, `docs:`, optional scope like `feat(bridge):`).
- Include in commit bodies any required hardware actions (reflash, daemon restart, cable swaps).
- Pull requests must summarize the problem, list commands/tests performed, capture hardware observations (logs, photos), and link issues/docs.

## Operational Notes

- Scripts assume Unix serial paths (`/dev/tty.usbmodem*`); translate to Windows `COMx` manually.
- Daemon artefacts: `/tmp/arduino_daemon.log` (logs) and `/tmp/arduino_daemon.pid` (PID). Clean them before retrying starts.
- Ember state: `~/.claude/ember_care_state.json` — never commit; reset via `scripts/feed_ember.py` if out-of-sync.

Codex agents should read `AGENTS.md` and `CLAUDE.md` for deeper architectural context before attempting major changes.
