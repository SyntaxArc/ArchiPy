# Protobuf DTOs

This guide demonstrates how to use the `BaseProtobufDTO` class to create Data Transfer Objects that can seamlessly convert between Pydantic models and Google Protocol Buffer messages.

## Overview

The `BaseProtobufDTO` provides a bridge between Pydantic DTOs and Protocol Buffers, enabling:

- **Bidirectional Conversion**: Convert from protobuf messages to Pydantic DTOs and vice versa
- **Type Safety**: Maintain type safety throughout the conversion process
- **Dependency Management**: Graceful handling when protobuf dependencies are not available
- **Validation**: Leverage Pydantic's validation capabilities with protobuf data

## Prerequisites

To use `BaseProtobufDTO`, you need to install the protobuf extra:

```bash
pip install archipy[protobuf]
```

Or install the protobuf dependency directly:

```bash
pip install google-protobuf
```

## Basic Usage

### 1. Define Your Protobuf Message

First, define your protobuf message (e.g., `user.proto`):

```protobuf
syntax = "proto3";

package user;

message User {
  string id = 1;
  string username = 2;
  string email = 3;
  string first_name = 4;
  string last_name = 5;
  bool is_active = 6;
  int64 created_at = 7;
}
```

### 2. Generate Python Code

Generate the Python protobuf code:

```bash
protoc --python_out=. user.proto
```

This creates `user_pb2.py` with your `User` message class.

### 3. Create Your DTO

```python
import logging
from datetime import datetime
from typing import ClassVar

from archipy.models.dtos.base_protobuf_dto import BaseProtobufDTO
from user_pb2 import User as UserProto

# Configure logging
logger = logging.getLogger(__name__)


class UserProtobufDTO(BaseProtobufDTO):
    """User DTO that can convert to/from protobuf messages."""

    # Specify the protobuf message class
    _proto_class: ClassVar[type[UserProto] | None] = UserProto

    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
```

### 4. Convert Between Formats

```python
# Create a protobuf message
proto_user = UserProto(
    id="123",
    username="john_doe",
    email="john@example.com",
    first_name="John",
    last_name="Doe",
    is_active=True,
    created_at=int(datetime.now().timestamp())
)

# Convert protobuf to DTO
try:
    user_dto = UserProtobufDTO.from_proto(proto_user)
except Exception as e:
    logger.error(f"Failed to convert from proto: {e}")
    raise
else:
    logger.info(f"User: {user_dto.first_name} {user_dto.last_name}")
    logger.info(f"Email: {user_dto.email}")

# Convert DTO back to protobuf
try:
    converted_proto = user_dto.to_proto()
except Exception as e:
    logger.error(f"Failed to convert to proto: {e}")
    raise
else:
    assert converted_proto.id == proto_user.id
    logger.info("Round-trip conversion successful")
```

## Advanced Usage

### Custom Field Mapping

You can customize field mapping by overriding the conversion methods:

```python
import logging
from datetime import datetime
from typing import ClassVar

from archipy.models.dtos.base_protobuf_dto import BaseProtobufDTO
from user_pb2 import User as UserProto

# Configure logging
logger = logging.getLogger(__name__)


class UserProtobufDTO(BaseProtobufDTO):
    """User DTO with custom field mapping."""

    _proto_class: ClassVar[type[UserProto] | None] = UserProto

    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_proto(cls, request: UserProto) -> "UserProtobufDTO":
        """Custom conversion from protobuf with field mapping."""
        # Convert timestamp to datetime
        created_at = datetime.fromtimestamp(request.created_at)

        return cls(
            id=request.id,
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            is_active=request.is_active,
            created_at=created_at
        )

    def to_proto(self) -> UserProto:
        """Custom conversion to protobuf with field mapping."""
        return UserProto(
            id=self.id,
            username=self.username,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            is_active=self.is_active,
            created_at=int(self.created_at.timestamp())
        )
```

### Nested DTOs

For complex nested structures:

```python
import logging
from typing import ClassVar

from archipy.models.dtos.base_protobuf_dto import BaseProtobufDTO
from user_pb2 import User as UserProto, UserList as UserListProto

# Configure logging
logger = logging.getLogger(__name__)


class UserProtobufDTO(BaseProtobufDTO):
    """User DTO."""

    _proto_class: ClassVar[type[UserProto] | None] = UserProto

    id: str
    username: str
    email: str


class UserListProtobufDTO(BaseProtobufDTO):
    """List of users DTO."""

    _proto_class: ClassVar[type[UserListProto] | None] = UserListProto

    users: list[UserProtobufDTO]
    total_count: int

    @classmethod
    def from_proto(cls, request: UserListProto) -> "UserListProtobufDTO":
        """Convert from protobuf with nested DTOs."""
        users = [UserProtobufDTO.from_proto(user) for user in request.users]

        return cls(
            users=users,
            total_count=request.total_count
        )

    def to_proto(self) -> UserListProto:
        """Convert to protobuf with nested DTOs."""
        users = [user.to_proto() for user in self.users]

        return UserListProto(
            users=users,
            total_count=self.total_count
        )
```

### Error Handling

The `BaseProtobufDTO` includes built-in error handling:

```python
# When protobuf is not installed
try:
    user_dto = UserProtobufDTO(id="123", username="test")
except RuntimeError as e:
    logger.error(f"Protobuf not available: {e}")
    # Handle gracefully - maybe use regular DTOs
    raise

# When _proto_class is not set
class IncompleteProtobufDTO(BaseProtobufDTO):
    id: str
    # Missing _proto_class

try:
    dto = IncompleteProtobufDTO(id="123")
    proto = dto.to_proto()  # Raises NotImplementedError
except NotImplementedError as e:
    logger.error(f"Proto class not configured: {e}")
    raise
```

## Best Practices

### 1. Always Set `_proto_class`

```python
class GoodProtobufDTO(BaseProtobufDTO):
    _proto_class: ClassVar[type[YourProto] | None] = YourProto
    # ... fields

class BadProtobufDTO(BaseProtobufDTO):
    # Missing _proto_class - will raise NotImplementedError
    pass
```

### 2. Handle Optional Dependencies

```python
try:
    from archipy.models.dtos.base_protobuf_dto import BaseProtobufDTO
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False

if PROTOBUF_AVAILABLE:
    BaseClass = BaseProtobufDTO
else:
    BaseClass = BaseDTO  # type: ignore[name-defined]  # Fallback to regular DTO
```

### 3. Use Type Annotations

```python
from typing import ClassVar

class UserProtobufDTO(BaseProtobufDTO):
    _proto_class: ClassVar[type[UserProto] | None] = UserProto
    # Always use proper type annotations
```

### 4. Validate Data

```python
from pydantic import Field

class UserProtobufDTO(BaseProtobufDTO):
    _proto_class: ClassVar[type[UserProto] | None] = UserProto

    id: str = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email address")

    # Pydantic validation will run during conversion
```

## Integration with Services

### gRPC Service Example

```python
import logging
from typing import ClassVar

from archipy.models.dtos.base_protobuf_dto import BaseProtobufDTO
from user_pb2 import User as UserProto

# Configure logging
logger = logging.getLogger(__name__)


class UserProtobufDTO(BaseProtobufDTO):
    _proto_class: ClassVar[type[UserProto] | None] = UserProto

    id: str
    username: str
    email: str


class UserService:
    def create_user(self, user_dto: UserProtobufDTO) -> UserProtobufDTO:
        """Create a user via gRPC."""
        try:
            # Convert DTO to protobuf for gRPC call
            proto_user = user_dto.to_proto()

            # Make gRPC call
            response_proto = self.grpc_client.CreateUser(proto_user)

            # Convert response back to DTO
            result = UserProtobufDTO.from_proto(response_proto)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
        else:
            logger.info(f"User created: {result.username}")
            return result

    def get_user(self, user_id: str) -> UserProtobufDTO:
        """Get a user via gRPC."""
        try:
            # Make gRPC call
            proto_user = self.grpc_client.GetUser(user_id)

            # Convert to DTO
            result = UserProtobufDTO.from_proto(proto_user)
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise
        else:
            logger.info(f"User retrieved: {result.username}")
            return result
```

## Testing

### Unit Tests

```python
import pytest
from datetime import datetime

from archipy.models.dtos.base_protobuf_dto import BaseProtobufDTO
from user_pb2 import User as UserProto


class TestUserProtobufDTO:
    def test_from_proto(self):
        # Arrange
        proto_user = UserProto(
            id="123",
            username="test_user",
            email="test@example.com"
        )

        # Act
        user_dto = UserProtobufDTO.from_proto(proto_user)

        # Assert
        assert user_dto.id == "123"
        assert user_dto.username == "test_user"
        assert user_dto.email == "test@example.com"

    def test_to_proto(self):
        # Arrange
        user_dto = UserProtobufDTO(
            id="123",
            username="test_user",
            email="test@example.com"
        )

        # Act
        proto_user = user_dto.to_proto()

        # Assert
        assert proto_user.id == "123"
        assert proto_user.username == "test_user"
        assert proto_user.email == "test@example.com"

    def test_round_trip_conversion(self):
        # Arrange
        original_dto = UserProtobufDTO(
            id="123",
            username="test_user",
            email="test@example.com"
        )

        # Act
        proto_user = original_dto.to_proto()
        converted_dto = UserProtobufDTO.from_proto(proto_user)

        # Assert
        assert converted_dto.id == original_dto.id
        assert converted_dto.username == original_dto.username
        assert converted_dto.email == original_dto.email
```

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'google.protobuf'**
   - Install the protobuf dependency: `pip install google-protobuf`

2. **NotImplementedError: Class is not mapped to a proto class**
   - Set the `_proto_class` attribute in your DTO

3. **TypeError: ClassVar parameter cannot include type variables**
   - Use concrete types instead of type variables in `ClassVar`

4. **Validation errors during conversion**
   - Ensure your protobuf message fields match your DTO fields
   - Check field types and required/optional status

### Debug Tips

```python
# Enable debug logging
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check protobuf availability
from archipy.models.dtos.base_protobuf_dto import PROTOBUF_AVAILABLE

logger.info(f"Protobuf available: {PROTOBUF_AVAILABLE}")

# Validate DTO structure
user_dto = UserProtobufDTO(id="123", username="test")  # type: ignore[name-defined]
logger.info(user_dto.model_dump())
```
