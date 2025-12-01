**Publishing**

This project includes two GitHub Actions workflows to publish distribution packages:

- **TestPyPI (automated)**: triggered on creating a tag like `vX.Y.Z`. Uploads to `https://test.pypi.org/legacy/`.
- **PyPI (manual)**: a `workflow_dispatch` workflow that requires manual confirmation to publish to production PyPI.

Required repository secrets / setup

- `TEST_PYPI_API_TOKEN` — API token created on https://test.pypi.org/ (Project-scoped token is recommended). Add it to GitHub repo Secrets.
- `PYPI_API_TOKEN` — Production API token created on https://pypi.org/. The production workflow uses this token by default for uploads. If you prefer OIDC/trusted publishing, adjust the workflow to remove the `password` input and enable `id-token: write` as needed.

Best practices applied

- Build and test dists in a separate job, then upload them as artifacts and publish in a job with limited elevated permissions (`id-token: write`) when using OIDC. The current production workflow uses `PYPI_API_TOKEN` by default.
- Use `pypa/gh-action-pypi-publish@release/v1` for uploads (pin to released action series).
- For TestPyPI the workflow sets `skip-existing: true` so repeated test uploads don't fail; for production it fails loudly on duplicates.
- Keep publishing jobs running on `ubuntu-latest` (recommended by the action authors).

How to publish

 - Test: tag the repository and push the tag. Example (preferred using `just`):

  just tag v1.2.3

Alternatively, this repository includes `just` recipes to perform tagging and publishing locally:

- Create and push a tag (usage: `just tag v1.2.3`):

  just tag v1.2.3

- Publish to TestPyPI using your `TEST_PYPI_API_TOKEN` environment variable:

  export TEST_PYPI_API_TOKEN="pypi-***"
  just publish-test

- Publish to production PyPI using your `PYPI_API_TOKEN` environment variable (be careful):

  export PYPI_API_TOKEN="pypi-***"
  just publish

- Production: Go to the Actions tab, open "Publish to PyPI (manual)", click "Run workflow", and set `confirm` to `yes`.

Security notes

- Trusted publishing (OIDC) is recommended where available, but this repo's production workflow defaults to token-based uploads. If you switch to OIDC, configure a publisher on PyPI and ensure `id-token: write` is set only for the publish job.
- Store API tokens in GitHub Secrets scoped to environments when possible.

Quick best-practices (summary from PyPA/PyPI):

- Use project-scoped API tokens when possible and set the username to `__token__` when using `twine` or CI uploads.
- Prefer Trusted Publishing (OIDC) for CI systems that support it; restrict `id-token: write` to the publish job only.
- Separate build and publish stages: build artifacts in a minimal, isolated job, upload as artifacts, then publish from a restricted job to make uploads atomic and reduce privilege exposure.
- Run `twine check dist/*` after building to catch metadata/long-description rendering issues before uploading.
- Use `skip-existing: true` for iterative TestPyPI uploads; keep it disabled for production to fail loudly on duplicates.
