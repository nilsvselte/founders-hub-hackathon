# Validation — 5 November 2026

Environment: Python 3.12.13; MCP Python SDK 1.30.0; httpx 0.28.1.
Dependency versions and hashes are pinned in `uv.lock`.

| Check | Result |
| --- | --- |
| `pytest -q` | 34 passed |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 11 files already formatted |
| Installed-package MCP subprocess from another working directory | Passed as part of the protocol integration test |
| `python scripts/demo.py` | Passed; synthetic search, reservation, listing, cancellation and empty final booking list |
| Public live read probe through the implemented client | Unauthenticated; 16 areas; 102 buildings |
| Unauthenticated live availability request | Access denied, represented as an actionable login error |
| Real authenticated booking/cancellation | Not run; Feide sign-in still required |

The actual fixture demo output is saved in `demo-transcript.txt`. All reservations
in that transcript are synthetic. Fixture HTTP traffic runs through
`httpx.MockTransport`, never the network.

The package was installed with `uv sync --frozen --no-editable --extra dev --extra login`.
This also checks that the built package can be imported without relying on the
source checkout being on Python's import path. After editing package source,
reinstall with `uv sync --frozen --no-editable --extra dev --extra login --reinstall-package tp-room-booking-mcp`
before repeating the installed-package checks.
