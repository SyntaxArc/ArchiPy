---
title: BDD Testing with ArchiPy
description: Guide and examples for writing BDD tests with ArchiPy.
---

# BDD Testing with ArchiPy

This page demonstrates how to use ArchiPy's integrated BDD testing capabilities with Behave.

## Basic Usage

ArchiPy provides a complete BDD testing setup using Behave. Here's how to use it:

### Feature Files

Create feature files in the `features` directory with Gherkin syntax:

```gherkin
# features/user_management.feature
Feature: User Management
  As a system administrator
  I want to manage users
  So that I can control system access

  Scenario: Create a new user
    Given I have admin privileges
    When I create a user with username "john" and email "john@example.com"
    Then the user should be saved in the database
    And the user should have default permissions
```

### Step Implementations

Implement the steps in Python files under `features/steps`:

```python
# features/steps/user_steps.py
import logging
from typing import Any

from behave import given, when, then

# NOTE: These imports are project-specific placeholders.
# Replace with your actual model/service imports in your application.
from app.models import User  # type: ignore[import-not-found]
from app.services import UserService  # type: ignore[import-not-found]
from archipy.models.errors import DatabaseQueryError, NotFoundError

# Configure logging
logger = logging.getLogger(__name__)

@given('I have admin privileges')
def step_impl(context: Any) -> None:  # noqa: F811
    """Set admin privileges in context."""
    context.is_admin = True
    logger.info("Admin privileges set")

@when('I create a user with username "{username}" and email "{email}"')
def step_impl(context: Any, username: str, email: str) -> None:  # noqa: F811
    """Create a user with the given username and email."""
    service = UserService()
    try:
        user = service.create_user(username, email)
    except Exception as e:
        # Proper exception chaining without operation message
        logger.error(f"Failed to create user: {e}")
        raise DatabaseQueryError(
            additional_data={"username": username, "email": email}
        ) from e
    else:
        context.user = user
        logger.info(f"User created: {username}")

@then('the user should be saved in the database')
def step_impl(context: Any) -> None:  # noqa: F811
    """Verify user exists in the database."""
    try:
        db_user = User.query.filter_by(username=context.user.username).first()
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise DatabaseQueryError() from e
    else:
        if db_user is None:
            raise NotFoundError(
                resource_type="user",
                additional_data={"username": context.user.username}
            )
        logger.info(f"User verified in database: {context.user.username}")

@then('the user should have default permissions')
def step_impl(context: Any) -> None:  # noqa: F811
    """Verify user has default permissions."""
    assert len(context.user.permissions) > 0, "User should have at least one permission"
    assert 'user:read' in context.user.permissions, "User should have user:read permission"
    logger.info(f"User has {len(context.user.permissions)} permissions")
```

### Running Tests

Run BDD tests using the Makefile command:

```bash
make behave
```

To run a specific feature:

```bash
uv run behave features/user_management.feature
```

To run a specific scenario by line number:

```bash
uv run behave features/user_management.feature:7
```

## Advanced BDD Testing

### Using Context Tables

Behave supports data tables for testing multiple scenarios:

```gherkin
Scenario: Create multiple users
Given I have admin privileges
When I create the following users:
| username | email              | role    |
| john     | john@example.com   | user    |
| alice    | alice@example.com  | admin   |
| bob      | bob@example.com    | support |
Then all users should be saved in the database
```

```python
@when('I create the following users')
def step_impl(context: Any) -> None:  # noqa: F811
    """Create multiple users from table data."""
    service = UserService()
    context.users = []
    for row in context.table:
        try:
            user = service.create_user(
                username=row['username'],
                email=row['email'],
                role=row['role']
            )
        except Exception as e:
            logger.error(f"Failed to create user {row['username']}: {e}")
            raise DatabaseQueryError(
                additional_data={"username": row['username'], "email": row['email']}
            ) from e
        else:
            context.users.append(user)
            logger.info(f"Created user: {row['username']}")
    logger.info(f"Created {len(context.users)} users total")
```

## See Also

- [Error Handling](error_handling.md) - Exception handling patterns with proper chaining
- [Examples Overview](index.md) - Overview of all examples
