````instructions
# GitHub Copilot Instructions for asynctasq

---

## Project Overview

Modern, async-first, type-safe task queue for Python inspired by Laravel. Multi-driver support (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS) with automatic ORM serialization via msgpack (90%+ payload reduction).

**Key Features:**
- True async-first architecture (asyncio)
- Native FastAPI integration
- 5 production-ready drivers
- ORM models serialized as PK references (SQLAlchemy, Django, Tortoise)
- Full type safety (`Generic[T]`, pyright strict mode)
- ACID guarantees, dead-letter queues, crash recovery, real-time events

## Essential Commands

```bash
just ci                # MANDATORY before commit: Format + Lint + Typecheck + Test
just check             # Quick validation (format + lint + typecheck only)
just test              # Run all tests
just docker-up         # Start test services (Redis, Postgres, MySQL, RabbitMQ, LocalStack)
just init              # Initial setup (run once)
```

---

## Development Boundaries

### ✅ ALWAYS DO (No Permission Needed)
- Research the web for the latest best practices for all languages/tools/libraries/packages/patterns used before implementing
- Run `just ci` before committing
- Add type hints to all public APIs (`def func() -> ReturnType:`)
- Write tests for new code (aim for >90% coverage)
- Use `async def` / `await` for all I/O operations
- Mock external I/O in unit tests (`AsyncMock`)
- Follow async-first principles (no blocking calls)
- Use environment variables for configuration
- Add docstrings for public APIs (Google style)
- Keep functions focused and under 50 lines
- Use descriptive variable names

### ⚠️ ASK FIRST (Breaking Changes)
- Modifying public API signatures
- Changing driver interfaces (`BaseDriver` protocol)
- Altering serialization format (breaks compatibility)
- Adding new dependencies to `pyproject.toml`
- Changing configuration structure (`Config` dataclass)
- Modifying worker lifecycle behavior
- Breaking backward compatibility
- Adding new drivers (requires full integration tests)

### 🚫 NEVER DO (Project Standards)
- Commit without `just ci` passing
- Use `Any` type without justification
- Block event loop with sync I/O in async context
- Skip writing tests ("I'll add them later")
- Hardcode secrets or configuration
- Mix async/sync code incorrectly
- Use `from module import *` (wildcard imports)
- Ignore security warnings (`just security`, `just audit`)
- Copy-paste code (extract to shared functions)
- Push directly to `main` branch (use PRs)

---

## Key Architecture Patterns

- **Tasks**: `@task` decorator or `Task[T]` base class with lifecycle hooks (`handle()`, `failed()`, `should_retry()`)
- **Drivers**: 5 backends (Redis, Postgres, MySQL, RabbitMQ, SQS) implementing `BaseDriver` protocol
- **Serialization**: msgpack with pluggable hooks for ORM models (90%+ payload reduction via PK references)
- **Worker**: Async polling loop with retry, timeout, graceful shutdown

---

## Workflow

1. Create feature branch
2. Make changes following code standards below
3. **Run `just ci`** (MUST pass)
4. Commit and create PR

---

## Testing

- **Framework**: pytest 9.0.1 with `asyncio_mode="strict"`
- **Markers**: `@pytest.mark.unit` or `@pytest.mark.integration`
- **Pattern**: AAA (Arrange, Act, Assert)
- **Async**: Use `@pytest.mark.asyncio` + `AsyncMock` for async code
- **Unit tests**: Mock all I/O. Fast (<1s per test)
- **Integration tests**: Real Docker services for driver testing
- **Never**: Make real API calls in tests

---

## Code Standards & Conventions

### Type Safety
- Full type hints on all public APIs (MUST pass `just typecheck`)
- Use `Generic[T]`, `list[str]`, `X | Y` (modern Python 3.9+ syntax)
- Avoid `Any` - use `object` or specific Union types
- Use `from __future__ import annotations` for forward references

### Code Style
- **Formatter**: ruff (line-length: 100)
- **Linter**: ruff with E, F, I, B, C4, UP rules
- **Docstrings**: Google style for public APIs
- **Complexity**: Max McCabe = 10

### Async-First
- Use `async def`/`await` for all I/O - NO blocking calls
- Use `await asyncio.sleep()` NOT `time.sleep()`
- Offload CPU-bound work to `ThreadPoolExecutor`
- Use `asyncio.Semaphore` for concurrency control
- Always await coroutines (Python warns if you forget)

### Error Handling
- Raise specific exceptions with context (task_id, queue, attempt)
- Use structured logging with `extra={}`
- Implement retry logic and dead-letter queues

---

## Key Files

- `src/asynctasq/core/task.py` - Task API (`@task` decorator, `Task[T]` base class)
- `src/asynctasq/core/worker.py` - Worker execution engine
- `src/asynctasq/drivers/` - Driver implementations (Redis, Postgres, MySQL, RabbitMQ, SQS)
- `src/asynctasq/integrations/fastapi.py` - FastAPI integration
- `src/asynctasq/config.py` - Configuration and env vars
- `docs/` - Full documentation with examples

---

## Configuration

All env vars use `ASYNCTASQ_` prefix. See `src/asynctasq/config.py` for complete list.

**Key settings**: `DRIVER` (redis|postgres|mysql|rabbitmq|sqs), `REDIS_URL`, `POSTGRES_DSN`, driver-specific config

---

## Before Committing

**MANDATORY: Run `just ci` - MUST pass with zero errors**

Then verify:
- ✅ Tests added (unit + integration if needed, >90% coverage)
- ✅ Type hints on all public APIs (`just typecheck` passes)
- ✅ Docstrings for public functions/classes
- ✅ Works with all 5 drivers (or limitations documented)
- ✅ No secrets in code (use env vars)

---

## Troubleshooting

- **Ruff issues**: Run `just format`
- **Type errors**: Add type hints, use `from __future__ import annotations`
- **Test failures**: Check `just docker-up` is running, run individual tests with `-v` flag
- **Import errors**: Run `just init` or `uv sync --all-extras --group dev`

---

## Best Practices

### ✅ DO:
- Run `just ci` before committing (non-negotiable)
- Write tests for all new code (>90% coverage)
- Use type hints on public APIs
- Follow async-first principles
- Keep tasks small and idempotent
- Log with structured context

### ❌ DON'T:
- Block event loop with sync I/O
- Use `Any` without justification
- Skip tests
- Hardcode secrets
- Break backward compatibility without major version bump

---

````