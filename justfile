# Default recipe to display help
default:
	@just --list

# Install package with all optional dependencies
install:
	uv sync --all-extras --group dev

# Setup pre-commit hooks
setup-hooks:
	uv run pre-commit install
	@echo "✅ Pre-commit hooks installed successfully!"

# Format code with Ruff
format:
	uv run ruff format .

# Auto-fix linting issues
lint-fix:
	uv run ruff check --fix .

# Type check with Pyright
typecheck:
	uv run pyright

# Run all checks (format, lint, typecheck)
check: format lint-fix typecheck
    @echo "✅ All checks passed"

# Run all CI checks locally (format, lint, typecheck, test)
ci: check test
	@echo "✅ All CI checks passed!"

# Run pre-commit on all files
pre-commit:
	uv run pre-commit run --all-files

# Run pre-commit autoupdate
pre-commit-update:
	uv run pre-commit autoupdate

# Start Docker services for testing
docker-up:
	docker-compose -f tests/infrastructure/docker-compose.yml up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 8
	@echo "🚀 Running database migrations..."
	-uv run python -m asynctasq migrate --driver postgres
	-uv run python -m asynctasq migrate --driver mysql
	@echo "✅ Docker services started and migrated"

# Stop Docker services
docker-down:
	docker-compose -f tests/infrastructure/docker-compose.yml down

# Restart Docker services
docker-restart:
	docker-compose -f tests/infrastructure/docker-compose.yml restart

# Start specific Docker services (usage: just docker-start-services redis postgres)
docker-start-services SERVICES:
	docker-compose -f tests/infrastructure/docker-compose.yml up -d {{SERVICES}}

# Stop specific Docker services (usage: just docker-stop-services redis postgres)
docker-stop-services SERVICES:
	docker-compose -f tests/infrastructure/docker-compose.yml down {{SERVICES}}

# Clean up cache files and directories
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.cover" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name ".coverage.*" -delete

# Run all tests
test:
	uv run pytest

# Run all tests with coverage report
test-cov:
	uv run pytest --cov=asynctasq --cov-branch --cov-report=term-missing --cov-report=html

# Show test coverage in browser
coverage-html: test-cov
	open htmlcov/index.html || xdg-open htmlcov/index.html

# Run tests with specific Python version
test-py VERSION:
	uv run --python {{VERSION}} pytest

# Run security checks with bandit
security:
	uv run bandit -r src/asynctasq -ll

# Run dependency security audit
audit:
	uv run pip-audit

# Show outdated dependencies
outdated:
	uv pip list --outdated

# Initialize project (install deps + setup hooks)
init: install setup-hooks
	@echo "✅ Project initialized successfully!"
	@echo "Run 'just services-up' to start Docker services"
	@echo "Run 'just test' to verify everything is working"

# Show ruff statistics
lint-stats:
	uv run ruff check --statistics .

# Profile tests (show slowest tests)
test-profile:
	uv run pytest --durations=10

# Run tests with verbose output
test-verbose:
	uv run pytest -vv

# Build the package
build:
	uv build

# Create and push a git tag (usage: just tag v1.2.3)
tag TAG:
	@if [ "$(printf '%s' '{{TAG}}' | cut -c1)" != "v" ]; then \
		echo "Tag should start with 'v', e.g. v1.2.3"; exit 1; \
	fi
	git tag -s {{TAG}}
	git push origin {{TAG}}
	@echo "✅ Pushed {{TAG}}"

# Delete a git tag locally and remotely (usage: just untag v1.2.3)
untag TAG:
	git tag -d {{TAG}}
	git push origin --delete {{TAG}}
	@echo "✅ Deleted tag {{TAG}} locally and remotely"

# Type check with Pyright
pyright:
	uv pip install pyright
	uv run pyright

# Show project info
info:
	@echo "Project: asynctasq"
	@echo "Python: $(uv run python --version)"
	@echo "UV: $(uv --version)"
	@echo ""
	@echo "Run 'just --list' to see all available commands"
