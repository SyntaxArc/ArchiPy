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

4. **Create a Branch**

   Create a branch for your feature or bugfix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

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

All contributions should include appropriate tests:

- **Unit Tests**: For testing individual components
- **Integration Tests**: For testing component interactions
- **BDD Tests**: For behavior-driven development

Run the tests to ensure your changes don't break existing functionality:

```bash
make test
make behave
```

### Documentation

All new features or changes should be documented:

- **Docstrings**: Update or add docstrings to document functions, classes, and methods
- **Type Annotations**: Include type annotations for all functions and methods
- **Documentation Files**: Update relevant documentation files if necessary

Building the documentation locally:

```bash
cd docs
make html
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

   Before submitting a pull request, make sure your branch is up to date with the main branch:

   ```bash
   git checkout main
   git pull origin main
   git checkout your-branch
   git rebase main
   ```

2. **Run All Checks**

   Ensure all checks pass:

   ```bash
   make check
   make test
   ```

3. **Submit Your Pull Request**

   Push your branch to your fork and create a pull request:

   ```bash
   git push origin your-branch
   ```

4. **Code Review**

   Your pull request will be reviewed by the maintainers. They may suggest changes or improvements.

5. **Merge**

   Once your pull request is approved, it will be merged into the main branch.

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

## Code of Conduct

Please note that ArchiPy has a code of conduct. By participating in this project, you agree to abide by its terms.

## Thank You

Thank you for contributing to ArchiPy! Your efforts help make the project better for everyone.
