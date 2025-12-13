# Contributing to ArchiPy 🏗️

First of all, thank you for considering contributing to ArchiPy! This document provides guidelines and instructions for
contributing to this project. By following these guidelines, you help maintain the quality and consistency of the
codebase.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
    - [Reporting Bugs](#reporting-bugs)
    - [Suggesting Enhancements](#suggesting-enhancements)
    - [Code Contributions](#code-contributions)
- [Development Setup](#development-setup)
    - [Prerequisites](#prerequisites)
    - [Installation for Development](#installation-for-development)
    - [Development Commands](#development-commands)
- [Pull Request Process](#pull-request-process)
- [Versioning](#versioning)
- [Getting Help](#getting-help)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md) that all contributors are expected to follow. Please
read the full text to understand what actions will and will not be tolerated.

## Ways to Contribute

### Reporting Bugs

Bug reports help us improve ArchiPy. When creating a bug report:

1. **Use a clear, descriptive title** that identifies the issue
2. **Provide detailed steps to reproduce** the problem
3. **Include specific examples** (code samples, error messages)
4. **Describe what you expected to happen** versus what actually happened
5. **Include screenshots or GIFs** if applicable
6. **List your environment details**: Python version, ArchiPy version, OS, etc.

### Suggesting Enhancements

Enhancement suggestions help ArchiPy evolve. When suggesting features:

1. **Use a clear, descriptive title**
2. **Provide a step-by-step description** of the suggested enhancement
3. **Explain why this enhancement would benefit** most ArchiPy users
4. **List any alternatives you've considered**
5. **Include mockups or examples** if applicable

### Code Contributions

We love code contributions! Here's the process:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Write code and tests** for your feature or fix
4. **Ensure all tests pass** and code meets quality standards
5. **Commit your changes**: `git commit -m 'Add some amazing feature'`
6. **Push to your branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request** with a clear description of the changes

### Documentation Improvements

Documentation is crucial for user experience. You can help by:

1. Fixing typos or clarifying existing documentation
2. Adding examples or use cases
3. Creating tutorials or how-to guides
4. Updating documentation to reflect new features

## Development Environment

### Prerequisites

Before contributing, ensure you have:

- **Python 3.14+**
- **UV** (dependency management)
- **Git**
- **make** (for running development commands)

### Setup Process

1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ArchiPy.git
   cd ArchiPy
   ```

2. **Set up the environment**:
   ```bash
   # Set up project pre-requisites (installs UV)
   make setup

   # Install development dependencies
   make install-dev
   ```

3. **Create a branch** for your work:
   ```bash
   git checkout -b your-feature-branch
   ```

### Useful Commands

ArchiPy provides commands via a Makefile to simplify development:

#### Environment Management

```bash
# Install core dependencies
make install

# Install development dependencies (including all extras)
make install-dev

# Update dependencies to their latest versions
make update
```

#### Code Quality

```bash
# Format code with Ruff formatter
make format

# Run all linters (ruff, ty)
make lint

# Run pre-commit hooks on all files
make pre-commit

# Run all checks (linting and tests)
make check
```

#### Testing

```bash
# Run BDD tests with behave
make behave
```

#### Building and Versioning

```bash
# Clean artifacts
make clean

# Build project distribution
make build

# Display current version
make version

# Bump versions
make bump-patch    # Bug fixes
make bump-minor    # New features
make bump-major    # Breaking changes
```

For a complete list:

```bash
make help
```

## Pull Request Process

1. **Ensure your code passes all checks**: Run `make check` locally
2. **Update documentation** if necessary
3. **Add tests** for new features or bug fixes
4. **Ensure compatibility** with Python 3.14+
5. **Verify all CI checks pass** on your PR

Pull requests are typically reviewed within a few days. Maintainers may request changes or clarifications about your
implementation.

## Versioning Guidelines

ArchiPy follows [Semantic Versioning](https://semver.org/):

- **Patch** (`make bump-patch`): Bug fixes and minor improvements
- **Minor** (`make bump-minor`): New features (backward compatible)
- **Major** (`make bump-major`): Breaking changes

## Getting Help

If you need assistance with contributing:

- **Open an issue** with your question
- **Contact maintainers**:
    - Hossein Nejati: [hosseinnejati14@gmail.com](mailto:hosseinnejati14@gmail.com)
    - Mehdi Einali: [einali@gmail.com](mailto:einali@gmail.com)
- **Consult documentation**: [https://archipy.readthedocs.io/](https://archipy.readthedocs.io/)

Thank you for contributing to ArchiPy! Your efforts help make this project better for everyone.
