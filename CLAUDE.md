# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Setup**: `uv sync --all-extras --all-groups` or `make install-dev`
- **Format**: `make format` (Ruff formatter, 120 char line length)
- **Lint**: `make lint` (Ruff + Ty)
- **Test**: `make behave` (all tests with Behave BDD framework)
- **Single test**: `uv run --extra behave behave features/file_name.feature`
- **Specific scenario**: `uv run --extra behave behave features/file_name.feature:line_number`
- **All checks**: `make check` (lint + security + test)
- **Pre-commit hooks**: `make pre-commit`
- **Security scan**: `make security` (Bandit)
- **Documentation**: `make docs-serve` (local MkDocs), `make docs-build`, `make docs-deploy`

## Architecture Overview

ArchiPy is a Python framework providing standardized, scalable architecture for modern applications. Built with Python 3.14+, it follows clean architecture principles with four main modules:

### 1. **Models** (`archipy/models/`)
Core data structures and domain layer:
- **Entities**: Domain model objects (`entities/`)
- **DTOs**: Data Transfer Objects for API input/output (`dtos/`)
- **Errors**: Custom exception classes (`errors/`)
- **Types**: Type definitions and enumerations (`types/`)

### 2. **Adapters** (`archipy/adapters/`)
External service integrations following Ports & Adapters pattern:
- **Database**: PostgreSQL, SQLite, StarRocks with SQLAlchemy integration
- **Cache**: Redis adapters with mocks
- **Services**: Email, Kafka, MinIO, Keycloak, Elasticsearch
- **Base**: Common adapter patterns and session management
Each adapter includes both implementations and testing mocks.

### 3. **Helpers** (`archipy/helpers/`)
Utility functions and support classes:
- **Utils**: General utilities (dates, strings, files, JWT, validation)
- **Decorators**: Function/class decorators (logging, timing, deprecation, atomic)
- **Interceptors**: Cross-cutting concerns (logging, tracing, validation)
- **Metaclasses**: Dynamic class generation utilities

### 4. **Configs** (`archipy/configs/`)
Configuration management with Pydantic models:
- Environment-based configuration loading
- Type-safe configuration through Pydantic Settings
- Support for multiple sources (env vars, files, etc.)

## Code Style

- **Python Version**: 3.14+ with modern type hints (`|` for unions, lowercase built-ins)
- **Imports**: Strict section order: `future → stdlib → third-party → first-party → local`
- **Typing**: Strict typing required with Ty (enabled via rules configuration)
- **Quotes**: Double quotes for all strings (inline and multiline)
- **Docstrings**: Google-style docstrings required for all public APIs
- **Naming**: Snake case for functions/vars, PascalCase for classes (enforced by Ruff)
- **Error handling**: Use specific exception types, preserve context with `raise ... from e`
- **Line length**: 120 characters maximum
- **Complexity**: Keep McCabe complexity below 10
- **Formatting**: Files end with newline, consistent indent (4 spaces)
