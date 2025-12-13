# Development

## Development Environment

### Set Up

1. Clone the repository:

   ```bash
   git clone https://github.com/SyntaxArc/ArchiPy.git
   cd ArchiPy
   ```

2. Initialize the project:

   ```bash
   make setup
   ```

3. Install dependencies:

   ```bash
   make install      # Core dependencies
   make install-dev  # All dependencies including dev tools
   ```

## Workflow

### Code Quality

Run checks:

```bash
make check  # Runs ruff, ruff format, ty
```

### Testing

Run tests:

```bash
make behave    # BDD tests
make ci        # Full pipeline
```

BDD tests use `behave` with feature files in `features/` and steps in `features/steps/`.

## Versioning

Follow [Semantic Versioning](https://semver.org/):

```bash
make bump-patch  # Bug fixes
make bump-minor  # New features
make bump-major  # Breaking changes
```

Add a message:

```bash
make bump-minor message="Added new utility"
```

## Build & Docs

Build the package:

```bash
make build
make clean  # Remove artifacts
```

Build docs:

```bash
cd docs
make html
```

Update dependencies:

```bash
make update  # Updates uv.lock with latest versions
```
