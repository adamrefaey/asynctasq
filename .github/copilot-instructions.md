Never run uv run pytest or just test, instead:
  **BEFORE implementing:** Research the web for latest best practices for all tools/libraries/patterns
  **WHILE implementing:** Run `just check` frequently to catch issues early
  **AFTER implementing:** Run `just ci` - MUST pass with zero errors before committing
`just ci` and test commands are expensive, so avoid running them unnecessarily. Use `just check` & scope test commands instead.
