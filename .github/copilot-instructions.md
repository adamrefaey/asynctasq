# GitHub Copilot Instructions for asynctasq

## 🚨 MANDATORY WORKFLOW

**YOU MUST follow these steps in order:**

1. **BEFORE implementing:** Research the web for latest best practices for all tools/libraries/patterns
2. **WHILE implementing:** Run `just check` frequently to catch issues early
3. **AFTER implementing:** Run `just ci` - MUST pass with zero errors before committing

---

## Project Overview

Async-first, type-safe task queue for Python 3.12+ inspired by Laravel. Multi-driver (Redis, PostgreSQL, MySQL, RabbitMQ, SQS), ORM-aware serialization (SQLAlchemy, Django, Tortoise), FastAPI integration.

**Stack:** Python 3.12+, asyncio, msgpack, pytest, ruff, pyright

---

## Commands

```bash
just check      # Format + Lint + Typecheck (fast validation)
just ci         # check + Test (MANDATORY before commit)
just test       # Run all tests
just docker-up  # Start test services (Redis, Postgres, etc.)
```

---

## Core Rules

### ✅ DO
- Full type hints on public APIs (`-> ReturnType`)
- Use `async def`/`await` for all I/O (NO blocking calls)
- Write tests for new code (>90% coverage, AAA pattern)
- Mock I/O in unit tests (`AsyncMock`)
- Use env vars for config (`ASYNCTASQ_` prefix)
- Google-style docstrings for public APIs
- Keep functions <50 lines

### 🚫 DON'T
- Commit without `just ci` passing
- Use `Any` without justification
- Block event loop (`time.sleep()`, sync DB calls, etc.)
- Skip tests
- Hardcode secrets
- Use wildcard imports (`from x import *`)

---

## Architecture

- **Tasks:** `tasks/` - Task definitions (`@task` decorator, `BaseTask`, `AsyncTask`, `SyncTask`)
- **Dispatcher:** `core/dispatcher.py` - Task dispatch API
- **Worker:** `core/worker.py` - Async execution engine with retry/timeout
- **Drivers:** `drivers/` - 5 backends implementing `BaseDriver` protocol
- **Events:** `core/events.py` - Real-time event streaming (Redis Pub/Sub)
- **Serialization:** `serializers/` - msgpack with ORM hooks (90%+ reduction)
- **Integrations:** `integrations/` - FastAPI, etc.

**Key patterns:**
- Tasks dispatch via `@task` decorator or `BaseTask` subclasses
- Drivers use async context managers for connections
- Events broadcast via Redis Pub/Sub
- ORM models serialize as PK references, re-fetch on execution

---

## Testing

- **Unit tests:** `@pytest.mark.unit` - Mock all I/O, <1s each
- **Integration tests:** `@pytest.mark.integration` - Real Docker services
- **Coverage:** >90% required (`just test-cov`)
- **Async:** Use `@pytest.mark.asyncio` + `AsyncMock`

---

## Type Safety

- Use `Generic[T]`, `list[str]`, `X | Y` (Python 3.12 syntax)
- Avoid `Any` - use `object` or specific unions
- Must pass `just typecheck` (pyright standard mode)
- Use `from __future__ import annotations` for forward refs

---

## Code Style

- **Formatter:** ruff (line-length: 100)
- **Linter:** ruff (E, F, I, B, C4, UP rules)
- **Complexity:** Max McCabe = 10
- Run `just format` for auto-fix

---

## Breaking Changes (ASK FIRST)

- Public API signatures
- Driver interfaces (`BaseDriver`)
- Serialization format
- New dependencies in `pyproject.toml`
- Config structure
- Worker lifecycle

---

## Troubleshooting

- **Format errors:** `just format`
- **Type errors:** Add hints, use `from __future__ import annotations`
- **Test failures:** Ensure `just docker-up` running
- **Import errors:** `uv sync --all-extras --group dev`

---
