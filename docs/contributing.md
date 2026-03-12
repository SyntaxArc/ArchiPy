---
title: Contributing
description: Guidelines for contributing to ArchiPy development and documentation.
---

# Contributing

Welcome to ArchiPy! We're excited that you're interested in contributing. This document outlines the process for
contributing to ArchiPy.

## Getting Started

1. **Fork the Repository**

   Fork the [ArchiPy repository](https://github.com/SyntaxArc/ArchiPy) on GitHub.

2. **Clone Your Fork**

   ```bash
   git clone https://github.com/YOUR-USERNAME/ArchiPy.git
   cd ArchiPy
   ```

3. **Set Up Development Environment**

   ```bash
   make setup
   make install
   make install-dev
   ```

   !!! tip "Pre-commit Hooks"
   Running `make install-dev` sets up pre-commit hooks that automatically run linting, formatting, and type checking on
   every commit. Use `make pre-commit` to run all hooks manually before opening a pull request.

4. **Create a Branch**

   Create a branch for your feature or bugfix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Installation

To set up a full local development environment from scratch:

```bash
# Clone the repository
git clone https://github.com/SyntaxArc/ArchiPy.git
cd ArchiPy

# Set up the project (installs UV)
make setup

# Install dependencies
make install

# Install all development tools and optional dependencies
make install-dev
```

!!! tip "Pre-commit Hooks"
Running `make install-dev` sets up pre-commit hooks that automatically run linting, formatting, and type checking on
every commit. Use `make pre-commit` to run all hooks manually before opening a pull request.

## Contribution Guidelines

### Code Style

ArchiPy follows a strict code style to maintain consistency across the codebase:

- **Ruff**: For linting and code formatting
- **Ty**: For type checking

All code must pass these checks before being merged:

```bash
make check
```

### Testing

All contributions must include appropriate BDD tests:

- **BDD Tests**: All tests are written as Gherkin scenarios in `features/`

Run the tests to ensure your changes don't break existing functionality:

```bash
make behave
```

### Documentation

All new features or changes should be documented:

- **Docstrings**: Update or add docstrings to document functions, classes, and methods
- **Type Annotations**: Include type annotations for all functions and methods
- **Documentation Files**: Update relevant documentation files if necessary

Building the documentation locally:

```bash
make docs-serve   # live-reload local server
make docs-build   # build static site
```

### Commit Messages

ArchiPy follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages:

```bash
<type>(<scope>): <description>
```

Common types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting changes
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

## Pull Request Process

1. **Update Your Branch**

   Before submitting a pull request, make sure your branch is up to date with the master branch:

   ```bash
   git checkout master
   git pull origin master
   git checkout your-branch
   git rebase master
   ```

2. **Run All Checks**

   Ensure all checks pass:

   ```bash
   make check
   make behave
   ```

3. **Submit Your Pull Request**

   Push your branch to your fork and create a pull request:

   ```bash
   git push origin your-branch
   ```

4. **Code Review**

   Your pull request will be reviewed by the maintainers. They may suggest changes or improvements.

5. **Merge**

   Once your pull request is approved, it will be merged into the master branch.

## Bug Reports and Feature Requests

If you find a bug or have a feature request, please create an issue on
the [GitHub issues page](https://github.com/SyntaxArc/ArchiPy/issues).

When reporting a bug, please include:

- A clear and descriptive title
- A detailed description of the bug
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Any relevant logs or error messages

When submitting a feature request, please include:

- A clear and descriptive title
- A detailed description of the feature
- Any relevant use cases
- If possible, a sketch of how the feature might be implemented

## How to Add a New Adapter

New adapters follow a consistent checklist. Use this as your guide when contributing an integration:

1. **Create the adapter package**

   ```
   archipy/adapters/<name>/
   ├── __init__.py
   ├── ports.py      # Abstract interface (plain class with @abstractmethod)
   ├── adapters.py   # Concrete implementation
   └── mocks.py      # In-memory test double
   ```

2. **Define the port** (`ports.py`)

   Create a plain class with `@abstractmethod` methods that describes what the adapter can do. Your business logic and
   repositories
   must depend only on this interface.

3. **Implement the adapter** (`adapters.py`)

   Implement the port against the real external service. Lazy-import the third-party library inside
   methods (not at module level) to avoid `ImportError` when the optional extra is not installed.

4. **Write the mock** (`mocks.py`)

   Implement the port using an in-memory data structure. The mock must behave consistently with the
   real adapter for all methods exercised in tests.

5. **Add the optional extra** to `pyproject.toml`

   ```toml
   [project.optional-dependencies]
   myservice = ["myservice-client>=1.0"]
   ```

6. **Write tests** — BDD tests using the mock for fast scenarios, integration tests using `testcontainers` for
   real-service scenarios.

7. **Document the adapter** — create both:
    - `docs/examples/adapters/<name>.md` — example guide (5 required sections)
    - `docs/api_reference/adapters/<name>.md` — API reference with mkdocstrings

8. **Update `mkdocs.yml`** — add both new pages under the appropriate `nav:` keys.

!!! note "Issue templates"
Use the [GitHub issue templates](https://github.com/SyntaxArc/ArchiPy/issues/new/choose) when
reporting bugs, requesting features, or proposing new adapters.

## Code of Conduct

Please note that ArchiPy has a code of conduct. By participating in this project, you agree to abide by its terms.

## Thank You

Thank you for contributing to ArchiPy! Your efforts help make the project better for everyone.

## Documentation Guidelines

This section outlines the standards and practices for ArchiPy documentation.

### Documentation Structure

- `mkdocs.yml` - Main configuration file for MkDocs
- `docs/` - Markdown documentation files
    - `index.md` - Get Started page
    - `api_reference/` - API documentation
    - `examples/` - Usage examples
    - `assets/` - Images and other static assets

### Format and Style

- Use Markdown syntax for all documentation files
- Follow the Google Python style for code examples
- Include type hints in code samples (using Python 3.14 syntax)
- Include proper exception handling with `raise ... from e` pattern
- Group related documentation in directories
- Link between documentation pages using relative links

### Code Examples

When including code examples:

1. Include proper type hints using Python 3.14 syntax (`x: list[str]` not `List[str]`)
2. Demonstrate proper error handling with exception chaining
3. Include docstrings with Args, Returns, and Raises sections
4. Show realistic use cases that align with ArchiPy's patterns
5. Keep examples concise but complete enough to understand usage

### Admonitions

Use Material for MkDocs admonitions to highlight important information:

```markdown
!!! note
This is a note.

!!! warning
This is a warning.

!!! tip
This is a tip.
```

### Building and Previewing Documentation

Preview the documentation locally:

```bash
make docs-serve
```

Build the documentation:

```bash
make docs-build
```

Deploy to GitHub Pages:

```bash
make docs-deploy
```

### Documentation Improvement Guidelines

When improving documentation:

1. Ensure clarity and conciseness
2. Include practical, runnable examples
3. Explain "why" not just "how"
4. Maintain logical navigation
5. Use diagrams for complex concepts
6. Validate that examples match the current API
7. Test code examples to ensure they work correctly
