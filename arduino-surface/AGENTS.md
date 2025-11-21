# Repository Guidelines

## Project Structure & Module Organization
- `firmware/agentic_surface/agentic_surface.ino`: Core Arduino sketch driving LCD, LEDs, servo, sensors.
- `bridge/surface_bridge.py`: Shared PySerial interface—keep protocol edits synced with firmware.
- `daemons/` + `scripts/`: Background workers and wrappers managing `/tmp/arduino_daemon.*`.
- `examples/`, `web_controller/`, `mcp-server/arduino_surface_mcp.py`: Demos and MCP adapter layered on the bridge.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` — set up Python deps.
- `arduino-cli compile --fqbn arduino:avr:uno firmware/agentic_surface` — verify the sketch before flashing.
- `bash scripts/start_agentic_stack.sh /dev/tty.usbmodemXXXX [daemon.py]` — launch the full agentic stack (enhanced daemon + Ember API); check with `scripts/daemon_status.sh` and stop via `scripts/stop_agentic_stack.sh`. Use `scripts/start_daemon.sh` directly only when experimenting with alternate daemons.
- `python3 mcp-server/arduino_surface_mcp.py` — start the JSON-RPC bridge after the daemon reports healthy.
- `python3 scripts/feed_ember.py` or `python3 examples/human_in_loop_example.py` — exercise Ember state and bridge calls.

## Coding Style & Naming Conventions
- Python: PEP 8, four-space indents, snake_case functions, typed public APIs.
- Keep imports side-effect free; route serial I/O through `ArduinoSurface`.
- Arduino: two-space indents, ALL_CAPS pins, tight helpers to fit UNO limits.
- Shell scripts: POSIX-friendly, guard against stale PID/log files, surface ✓/✗ output.

## Testing Guidelines
- Use `python3 examples/arc2_puzzle_interface.py` or `human_in_loop_example.py` for repeatable smoke tests.
- After firmware edits, run `arduino-cli compile` and confirm the serial `"status":"ready"` handshake.
- Add lightweight `pytest` cases (`tests/test_*.py`) and document manual verification steps plus ports in PRs.

## Commit & Pull Request Guidelines
- Apply Conventional Commits (`feat:`, `fix:`, `docs:`) with ≤72 char subjects and optional scope (`feat(bridge):`).
- Summaries should flag user-visible changes and any needed reflashes or daemon restarts.
- PRs include a problem statement, command log/screens, hardware notes, and linked issues or docs.

## Configuration & Operational Notes
- Default scripts expect Unix-style ports (`/dev/tty.usbmodem*`); map to Windows `COM` manually.
- Logs and PID files live under `/tmp/arduino_daemon.{log,pid}`—clear them when debugging.
- Ember state resides at `~/.claude/ember_care_state.json`; never commit it, reset via `scripts/feed_ember.py` if it drifts.
