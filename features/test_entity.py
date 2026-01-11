import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Synonym, relationship

from archipy.models.entities.sqlalchemy.base_entities import (
    BaseEntity,
    UpdatableAdminEntity,
    UpdatableDeletableEntity,
    UpdatableManagerEntity,
)


class TestEntity(UpdatableDeletableEntity):
    """A test entity class for use in SQLAlchemy tests.

    Extends the UpdatableDeletableEntity class which provides created_at,
    updated_at and is_deleted fields.

    Attributes:
        test_uuid (uuid.UUID): Primary key UUID
        pk_uuid (uuid.UUID): Synonym for test_uuid, following the BaseEntity pattern
        description (str): Text field for testing string operations
        related_entities (List[RelatedTestEntity]): For testing relationships
    """

    __tablename__ = "test_entities"

    __table_args__ = {
        "comment": "Test entity table",
        "starrocks_primary_key": "test_uuid",
        "starrocks_distributed_by": "HASH(test_uuid) BUCKETS 10",
        "starrocks_properties": {"replication_num": "1"},
    }

    test_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pk_uuid = Synonym("test_uuid")

    description = Column(String, nullable=True)

    # Add relationship for testing complex scenarios
    related_entities = relationship("RelatedTestEntity", back_populates="parent", cascade="all, delete-orphan")

    def __init__(
        self,
        test_uuid: uuid.UUID,
        created_at: datetime,
        description: str | None = None,
        updated_at: datetime | None = None,
        is_deleted: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize a new TestEntity.

        Args:
            test_uuid: UUID for testing uniqueness, also serves as primary key
            created_at: Creation timestamp
            description: Optional description field
            updated_at: Optional update timestamp
            is_deleted: Whether the entity is soft-deleted
            **kwargs: Additional keyword arguments for extensibility
        """
        # Set the primary key
        self.test_uuid = test_uuid

        # We don't call super().__init__ since BaseEntity expects a server_default
        # for created_at, but in tests we need to control this value
        self.created_at = created_at
        self.description = description

        if updated_at:
            self.updated_at = updated_at

        self.is_deleted = is_deleted


class TestManagerEntity(UpdatableManagerEntity):
    """A test entity with manager attributes for testing.

    Extends UpdatableManagerEntity to include manager-related fields.

    Attributes:
        test_uuid (uuid.UUID): Primary key UUID
        pk_uuid (uuid.UUID): Synonym for test_uuid, following the BaseEntity pattern
        description (str): Text field for testing string operations
        created_by_uuid (uuid.UUID): UUID of the manager who created this entity
        updated_by_uuid (uuid.UUID): UUID of the manager who last updated this entity
    """

    __tablename__ = "test_manager_entities"

    __table_args__ = {
        "comment": "Test manager entity table",
        "starrocks_primary_key": "test_uuid",
        "starrocks_distributed_by": "HASH(test_uuid) BUCKETS 10",
        "starrocks_properties": {"replication_num": "1"},
    }

    test_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pk_uuid = Synonym("test_uuid")

    description = Column(String, nullable=True)

    # Manager-related fields required by ManagerMixin and UpdatableManagerMixin
    created_by_uuid = Column(UUID(as_uuid=True), nullable=False)
    updated_by_uuid = Column(UUID(as_uuid=True), nullable=True)

    def __init__(
        self,
        test_uuid: uuid.UUID,
        created_at: datetime,
        created_by_uuid: uuid.UUID,
        description: str | None = None,
        updated_at: datetime | None = None,
        updated_by_uuid: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new TestManagerEntity.

        Args:
            test_uuid: UUID for testing uniqueness, also serves as primary key
            created_at: Creation timestamp
            created_by_uuid: UUID of the manager who created this entity
            description: Optional description field
            updated_at: Optional update timestamp
            updated_by_uuid: UUID of the manager who last updated this entity
            **kwargs: Additional keyword arguments for extensibility
        """
        # Set the primary key
        self.test_uuid = test_uuid

        self.created_at = created_at
        self.description = description
        self.created_by_uuid = created_by_uuid

        if updated_at:
            self.updated_at = updated_at

        self.updated_by_uuid = updated_by_uuid


class TestAdminEntity(UpdatableAdminEntity):
    """A test entity with admin attributes for testing.

    Extends UpdatableAdminEntity to include admin-related fields.

    Attributes:
        test_uuid (uuid.UUID): Primary key UUID
        pk_uuid (uuid.UUID): Synonym for test_uuid, following the BaseEntity pattern
        description (str): Text field for testing string operations
        created_by_admin_uuid (uuid.UUID): UUID of the admin who created this entity
        updated_by_admin_uuid (uuid.UUID): UUID of the admin who last updated this entity
    """

    __tablename__ = "test_admin_entities"

    __table_args__ = {
        "comment": "Test admin entity table",
        "starrocks_primary_key": "test_uuid",
        "starrocks_distributed_by": "HASH(test_uuid) BUCKETS 10",
        "starrocks_properties": {"replication_num": "1"},
    }

    test_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pk_uuid = Synonym("test_uuid")

    description = Column(String, nullable=True)

    # Admin-related fields required by AdminMixin and UpdatableAdminMixin
    created_by_admin_uuid = Column(UUID(as_uuid=True), nullable=False)
    updated_by_admin_uuid = Column(UUID(as_uuid=True), nullable=True)

    def __init__(
        self,
        test_uuid: uuid.UUID,
        created_at: datetime,
        created_by_admin_uuid: uuid.UUID,
        description: str | None = None,
        updated_at: datetime | None = None,
        updated_by_admin_uuid: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new TestAdminEntity.

        Args:
            test_uuid: UUID for testing uniqueness, also serves as primary key
            created_at: Creation timestamp
            created_by_admin_uuid: UUID of the admin who created this entity
            description: Optional description field
            updated_at: Optional update timestamp
            updated_by_admin_uuid: UUID of the admin who last updated this entity
            **kwargs: Additional keyword arguments for extensibility
        """
        # Set the primary key
        self.test_uuid = test_uuid

        self.created_at = created_at
        self.description = description
        self.created_by_admin_uuid = created_by_admin_uuid

        if updated_at:
            self.updated_at = updated_at

        self.updated_by_admin_uuid = updated_by_admin_uuid


class RelatedTestEntity(BaseEntity):
    """A related test entity for testing relationships with TestEntity.

    Extends the BaseEntity class with a relationship to TestEntity.

    Attributes:
        related_uuid (uuid.UUID): Primary key UUID
        pk_uuid (uuid.UUID): Synonym for related_uuid, following the BaseEntity pattern
        name (str): Name of the related entity
        value (str): Value for testing
        parent_id (uuid.UUID): Foreign key to TestEntity
        parent (TestEntity): Relationship to parent TestEntity
    """

    __tablename__ = "related_test_entities"

    __table_args__ = {
        "comment": "Related test entity table",
        "starrocks_primary_key": "related_uuid",
        "starrocks_distributed_by": "HASH(related_uuid) BUCKETS 10",
        "starrocks_properties": {"replication_num": "1"},
    }

    related_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pk_uuid = Synonym("related_uuid")

    name = Column(String, nullable=False)
    value = Column(String, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("test_entities.test_uuid"), nullable=False)

    # Relationship to parent
    parent = relationship("TestEntity", back_populates="related_entities")

    def __init__(
        self,
        name: str,
        parent_id: uuid.UUID,
        related_uuid: uuid.UUID | None = None,
        created_at: datetime = None,
        value: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new RelatedTestEntity.

        Args:
            name: Name of the related entity
            parent_id: Foreign key to parent TestEntity
            related_uuid: Primary key UUID (autogenerated if not provided)
            created_at: Creation timestamp (defaults to current time if not provided)
            value: Optional value field
            **kwargs: Additional keyword arguments for extensibility
        """
        # Set the primary key if provided
        if related_uuid:
            self.related_uuid = related_uuid

        if created_at:
            self.created_at = created_at
        else:
            self.created_at = datetime.now()

        self.name = name
        self.parent_id = parent_id
        self.value = value
