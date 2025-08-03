# Contributing to Flare AI Kit

First off, thank you for considering contributing to Flare AI Kit!

We welcome contributions from the community to help make this SDK robust, feature-rich, and easy to use.

## How to Contribute

- **Pull Requests (PRs)** for bug fixes, features, and documentation updates.
- **Bug Reports** for issues you encounter.

## ✨ Write High-Quality Code

We strive for high-quality, maintainable code. Please adhere to the following principles:

1.  **Clean Interfaces & Simplicity:**

    - Follow the Zen of Python principle: "There should be one-- and preferably only one --obvious way to do it."
    - Design clear, minimal, and predictable interfaces for functions and classes.
    - Use descriptive names for variables, functions, and classes.
    - Keep code focused and avoid unnecessary complexity.

2.  **Formatting, Linting & Type-Checking:**

    - Use [ruff](https://docs.astral.sh/ruff/) for formatting and linting, both settings are defined in `pyproject.toml`.
    - Use [pyright](https://github.com/microsoft/pyright) for type checking, all new code MUST include accurate type hints.
    - Avoid using `typing.Any` unless absolutely necessary and clearly justified in comments.
    - You can also install [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) into VSCode for an easier experience.
    - Ensure your code passes all checks locally without errors:
      ```bash
      uv run ruff format
      uv run ruff check --fix
      uv run pyright
      ```

3.  **Use dependencies sparingly:**
    - Every dependency added is a potential security risk.
    - If the dependency is required, it should live in under `[project.optional-dependencies]` with a key marking the high level function, e.g. `rag`, `consensus`.

## 🧪 Test Extensively

- New features **must** include appropriate unit and/or integration tests using `pytest`.
- Bug fixes **should** include tests demonstrating the fix.
- **All tests must pass** locally before submitting a pull request. Run tests via:

  ```bash
  # Run all tests (unit + integration, requires env vars for integration)
  uv run pytest
  ```

## 🚨 CI Checks Must Pass

- We use Continuous Integration (CI) pipelines (e.g., GitHub Actions) to automatically run linters, type checkers, and tests.
- **Pull requests will only be considered for merging if all CI checks pass.** Ensure your code meets all quality gates before submitting.

## ✅ Use Conventional Commits

- All commit messages **MUST** adhere to the **Conventional Commits** specification. This helps automate changelog generation and provides a clear commit history.
- Please read the specification: [https://www.conventionalcommits.org/](https://www.conventionalcommits.org/)
- **Format:** `<type>[optional scope]: <description>`
- **Examples:**
  - `feat(rag): add support for Neo4j AuraDB connection`
  - `fix(ecosystem): correct decimal calculation in FTSO price feed`
  - `docs(readme): update README with installation instructions`
  - `test(rag): add unit tests for GraphDbSettingsModel`
  - `chore(deps): update ruff version in pyproject.toml`

## 📜 License

By contributing to Flare AI Kit, you agree that your contributions will be licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for more information.

Thank you for contributing!
