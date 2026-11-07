# Guide for Contributing Agents

Read this before changing anything in the repo.

## 1. Orient
1. Read [master_repository_specification.md](master_repository_specification.md) – the source of truth for architecture, ports, and endpoints.
2. Read [backlog.md](backlog.md) – pick an unowned task or add one.

## 2. Claiming and working a task
1. Set the task's **Owner** to your agent name/ID and Status to `[~]` in `backlog.md` *before* starting.
2. Keep changes scoped to the task. Don't refactor unrelated code.
3. Preserve existing comments and docstrings unrelated to your change.
4. Respect the spec: ports (Pi 5000/5001, laptop 8080), endpoint names, and the repo layout.
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
- Python 3; dependencies go in `laptop_vision/requirements.txt` (laptop) or are documented in a comment/README (Pi-only, e.g. `picamera2`).
- Never commit model weights larger than reasonable or secrets; document where models go in `laptop_vision/models/README.md`.
- Pi-only code (`pi_edge/`) can't run on Windows; don't claim it as tested unless run on the Pi.

## 5. Verification
- Run what you can (syntax check with `python -m py_compile <file>`, run laptop pieces).
- State clearly what was and wasn't tested in your task note.

## 6. Handoff report
End your work with a short summary: files changed, backlog items updated/added, what remains, and known issues.
