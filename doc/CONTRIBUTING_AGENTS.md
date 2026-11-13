# Guide for Contributing Agents

Read this before changing anything in the repo.

## 1. Orient
1. Read [smart_helmet_software_poc_plan.md](smart_helmet_software_poc_plan.md) and [smart_helmet_module_product_plan.md](smart_helmet_module_product_plan.md) – the sources of truth for architecture, sensors, and product scope.
2. Read [backlog.md](backlog.md) – pick an unowned task or add one.

## 2. Claiming and working a task
1. Set the task's **Owner** to your agent name/ID and Status to `[~]` in `backlog.md` *before* starting.
2. Keep changes scoped to the task. Don't refactor unrelated code.
3. Preserve existing comments and docstrings unrelated to your change.
4. Respect the architecture: keep `poc/` modules decoupled, non-blocking (`asyncio`), and testable in `--mock` mode without Pi hardware.
5. When done, set Status to `[x]`, move the item to **Done**, and add a one-line note of what changed and any caveats.

## 3. Adding to the backlog (cowork)
Any agent that finds a bug, gap, or idea must add a row to the backlog table:
- **ID:** next sequential `T-NNN` (check the last row; don't reuse IDs).
- **Pri:** P0 blocker / P1 important / P2 nice to have.
- **Status:** `[ ]`.
- **Task:** one actionable sentence, with file paths where relevant.
- **Owner:** `unassigned` unless you are taking it.

Concurrent edits: re-read `backlog.md` immediately before editing, change only your own rows plus appended rows, and don't reorder or renumber others' rows.

## 4. Code standards
- Python 3.9+; portable dependencies go in `requirements.txt`, and Pi-only hardware/AI dependencies (e.g. `picamera2`, `smbus2`, `tflite-runtime`) go in `requirements-pi.txt`.
- Never commit model weights (`.tflite`) or secrets; document where models go when adding weight download/setup instructions.
- Pi-only hardware paths (UART, I2C, CSI camera, Bluetooth audio) can't run on Windows; don't claim hardware paths as tested unless run on the Pi.

## 5. Verification
- Run what you can (`python -m unittest discover -s tests -v`, `python -m poc.main_controller --mock --duration 3`).
- State clearly what was and wasn't tested in your task note.

## 6. Handoff report
End your work with a short summary: files changed, backlog items updated/added, what remains, and known issues.
