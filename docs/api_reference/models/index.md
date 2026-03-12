# Models

The `models` module contains the domain layer data structures — entities, DTOs, errors, and types. This layer holds no business logic or I/O; it defines only the shapes of data flowing through the application.

## Submodules

| Submodule | Description |
|---|---|
| [DTOs](dtos.md) | Pydantic data transfer objects for API input/output |
| [Entities](entities.md) | SQLAlchemy ORM entity base classes |
| [Errors](errors.md) | Custom exception hierarchy |
| [Types](types.md) | Enumerations and shared type definitions |

## Source Code

📁 Location: `archipy/models/`

🔗 [Browse Source](https://github.com/SyntaxArc/ArchiPy/tree/master/archipy/models)

## API Stability

| Component | Status | Notes |
|---|---|---|
| DTOs | 🟢 Stable | Production-ready |
| Entities | 🟢 Stable | Production-ready |
| Errors | 🟢 Stable | Production-ready |
| Types | 🟢 Stable | Production-ready |
