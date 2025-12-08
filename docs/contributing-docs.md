# ArchiPy Documentation Guidelines

This document outlines the standards and practices for ArchiPy documentation.

## Documentation Structure

- `mkdocs.yml` - Main configuration file for MkDocs
- `docs/` - Markdown documentation files
    - `index.md` - Home page
    - `api_reference/` - API documentation
    - `examples/` - Usage examples
    - `assets/` - Images and other static assets

## Writing Documentation

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

## Building and Previewing Documentation

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

## Documentation Improvement Guidelines

When improving documentation:

1. Ensure clarity and conciseness
2. Include practical, runnable examples
3. Explain "why" not just "how"
4. Maintain logical navigation
5. Use diagrams for complex concepts
6. Validate that examples match the current API
7. Test code examples to ensure they work correctly
