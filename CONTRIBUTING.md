# Contributing to AsyncTasQ

Thank you for your interest in contributing to AsyncTasQ! We welcome contributions from the community.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork:**
   ```bash
   git clone https://github.com/yourusername/asynctasq.git
   cd asynctasq
   ```
3. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
4. **Install dependencies:**
   ```bash
   uv sync --all-extras --group dev
   ```
5. **Set up pre-commit hooks:**
   ```bash
   uv run pre-commit install
   ```

## Development Workflow

### Running Tests

We use `pytest` for testing with markers to distinguish test types:

```bash
# Run all tests
uv run pytest

# Run only unit tests (fast, no external dependencies)
uv run pytest -m unit

# Run only integration tests (requires Docker services)
uv run pytest -m integration

# Run tests with coverage report
uv run pytest --cov=asynctasq --cov-branch --cov-report=term-missing --cov-report=html

# Run a specific test file
uv run pytest tests/unit/core/test_task.py

# Run tests matching a pattern
uv run pytest -k "test_dispatch"
```

**Test Markers:**

- `@pytest.mark.unit` - Unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (require Docker services)

### Integration Tests with Docker

Integration tests require Docker services (Redis, PostgreSQL, MySQL, LocalStack for SQS):

```bash
# Start Docker services
docker-compose -f tests/infrastructure/docker-compose.yml up -d

# Run integration tests
uv run pytest -m integration

# Stop Docker services
docker-compose -f tests/infrastructure/docker-compose.yml down
```

**Available Services:**

- Redis: `localhost:6379`
- PostgreSQL: `localhost:5432` (user: `test`, password: `test`, db: `test_db`)
- MySQL: `localhost:3306` (user: `test`, password: `test`, db: `test_db`)
- LocalStack (SQS): `localhost:4566`

### Code Quality

We use `ruff` for linting and formatting, and `pyright` for type checking:

```bash
# Format code
uv run ruff format .

# Check code style
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type checking
uv run pyright
```

**Code Style Guidelines:**

- Line length: 100 characters
- Target Python version: 3.11+
- We use `ruff` with strict linting rules (pycodestyle, pyflakes, isort, flake8-bugbear, etc.)

### Using Just Commands

We provide a `justfile` with convenient commands:

```bash
# Run all tests
just test

# Run unit tests only
just test-unit

# Run integration tests (starts Docker automatically)
just test-integration-docker

# Run tests with coverage
just test-cov

# Clean cache files
just clean
```

## Making Changes

1. **Create a new branch:**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes** following our code style guidelines

3. **Add tests** for your changes:

   - Unit tests for core logic
   - Integration tests for driver-specific functionality
   - Ensure tests pass: `uv run pytest`

4. **Run code quality checks:**

   ```bash
   uv run ruff format .
   uv run ruff check .
   uv run pyright
   ```

5. **Commit your changes:**

   ```bash
   git commit -m "Add feature: clear description of your changes"
   ```

6. **Push to your fork:**

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a pull request** on GitHub

## Pull Request Guidelines

- **Write clear, descriptive commit messages** following conventional commits format
- **Include tests** for new features and bug fixes
- **Update documentation** as needed (README, docstrings, etc.)
- **Ensure all CI checks pass** (tests, linting, type checking)
- **Reference related issues** in your PR description (e.g., "Fixes #123")
- **Keep PRs focused** - one feature or fix per PR
- **Add examples** if introducing new functionality

## Code Review Process

1. A maintainer will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged

We aim to review PRs within 48 hours. If you haven't received feedback after a week, feel free to ping us.

## Development Tips

### Project Structure

- `src/asynctasq/` - Main source code
- `tests/unit/` - Unit tests (no external dependencies)
- `tests/integration/` - Integration tests (require Docker services)
- `tests/infrastructure/` - Docker Compose configuration for test services

### Adding New Drivers

If you're adding a new queue driver:

1. Create driver class in `src/asynctasq/drivers/`
2. Inherit from `BaseDriver`
3. Implement required methods: `connect()`, `disconnect()`, `enqueue()`, `dequeue()`, etc.
4. Add unit tests in `tests/unit/drivers/`
5. Add integration tests in `tests/integration/drivers/`
6. Update `DriverFactory` to support the new driver
7. Update documentation

### Adding New ORM Support

If you're adding support for a new ORM:

1. Extend `OrmHandler` in `src/asynctasq/serializers/orm_handler.py`
2. Add detection logic for the ORM model type
3. Implement serialization (model → reference)
4. Implement deserialization (reference → model)
5. Add integration tests with the ORM
6. Update documentation

## Questions?

Feel free to:

- Open an issue for questions or concerns
- Start a discussion in GitHub Discussions
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
