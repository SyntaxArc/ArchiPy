from datetime import datetime
from typing import ClassVar

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Synonym, mapped_column

PK_COLUMN_NAME = "pk_uuid"


# Root base class
class BaseEntity(DeclarativeBase):
    """Base class for all SQLAlchemy models with automatic timestamps.

    This class serves as the base for all entities in the application. It provides
    common functionality such as automatic timestamping for `created_at` and
    validation for the primary key column.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
    """

    __abstract__ = True
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)

    @classmethod
    def _is_abstract(cls) -> bool:
        """Check if the class is abstract.

        Returns:
            bool: True if the class is abstract, False otherwise.
        """
        return (not hasattr(cls, "__tablename__")) and cls.__abstract__

    def __init_subclass__(cls, **kw: object) -> None:
        """Validate the subclass during initialization.

        Args:
            **kw: Additional keyword arguments passed to the subclass.

        Raises:
            AttributeError: If the subclass does not have the required primary key column.
        """
        if cls._is_abstract():
            return
        cls._validate_pk_column()
        super().__init_subclass__(**kw)

    @classmethod
    def _validate_pk_column(cls) -> None:
        """Validate that the subclass has the required primary key column.

        Raises:
            AttributeError: If the primary key column is missing or invalid.
        """
        if not hasattr(cls, PK_COLUMN_NAME):
            error_message = f"Child class {cls.__name__} must have {PK_COLUMN_NAME}"
            raise AttributeError(error_message)
        pk_column = getattr(cls, PK_COLUMN_NAME)
        if not isinstance(pk_column, Synonym):
            error_message = f"{PK_COLUMN_NAME} must be a sqlalchemy.orm.Synonym type"
            raise TypeError(error_message)


# Utility class for mixins
class EntityAttributeChecker:
    """Utility class for validating model attributes.

    This class provides functionality to ensure that at least one of the specified
    attributes is present in a model.

    Attributes:
        required_any: A list of lists, where each inner list contains
            attribute names. At least one attribute from each inner list must be present.
    """

    required_any: ClassVar[list[list[str]]] = []

    @classmethod
    def validate(cls, base_class: type) -> None:
        """Validate that at least one of the required attributes is present.

        Args:
            base_class: The class to validate.

        Raises:
            AttributeError: If none of the required attributes are present.
        """
        for attrs in cls.required_any:
            if not any(hasattr(base_class, attr) for attr in attrs):
                error_message = f"One of {attrs} must be defined in {base_class.__name__}"
                raise AttributeError(error_message)


# Independent mixins
class DeletableMixin:
    """Mixin to add a deletable flag to models.

    This mixin adds an `is_deleted` column to indicate whether the entity has been
    soft-deleted, allowing for logical deletion without physically removing records.

    Attributes:
        is_deleted: Flag indicating if the entity is deleted.
    """

    __abstract__ = True
    is_deleted = Column(Boolean, default=False, nullable=False)


class UpdatableMixin:
    """Mixin to add updatable timestamp functionality.

    This mixin adds an `updated_at` column to track the last update time of the entity,
    automatically maintaining a timestamp of the most recent modification.

    Attributes:
        updated_at: Timestamp indicating when the entity was last updated.
    """

    __abstract__ = True

    updated_at = Column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
    )


class ArchivableMixin:
    """Mixin to add Archivable functionality.

    This mixin adds an `is_archived` column to indicate whether the entity has been
    archived, and an `origin_uuid` column to reference the original entity.

    Attributes:
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
    """

    __abstract__ = True
    is_archived = Column(Boolean, default=False, nullable=False)
    # Using Column without Mapped is acceptable since Column works with BaseEntity.__table__
    origin_uuid = Column(ForeignKey("self.pk_uuid"), nullable=True)


# Mixins dependent on EntityAttributeChecker
class AdminMixin(EntityAttributeChecker):
    """Mixin for models with admin-related attributes.

    This mixin ensures that at least one of the admin-related attributes is present,
    providing tracking of which administrator created the entity.

    Attributes:
        required_any: Specifies the required admin-related attributes.
    """

    __abstract__ = True
    required_any: ClassVar[list[list[str]]] = [["created_by_admin", "created_by_admin_uuid"]]

    def __init_subclass__(cls, **kw: object) -> None:
        """Validate the subclass during initialization.

        Args:
            **kw: Additional keyword arguments passed to the subclass.
        """
        cls.validate(cls)
        super().__init_subclass__(**kw)


class ManagerMixin(EntityAttributeChecker):
    """Mixin for models with manager-related attributes.

    This mixin ensures that at least one of the manager-related attributes is present,
    providing tracking of which manager created the entity.

    Attributes:
        required_any: Specifies the required manager-related attributes.
    """

    __abstract__ = True
    required_any: ClassVar[list[list[str]]] = [["created_by", "created_by_uuid"]]

    def __init_subclass__(cls, **kw: object) -> None:
        """Validate the subclass during initialization.

        Args:
            **kw: Additional keyword arguments passed to the subclass.
        """
        cls.validate(cls)
        super().__init_subclass__(**kw)


class UpdatableAdminMixin(EntityAttributeChecker):
    """Mixin for models updatable by admin.

    This mixin ensures that at least one of the admin-related update attributes is present,
    providing tracking of which administrator last updated the entity.

    Attributes:
        required_any: Specifies the required admin-related update attributes.
    """

    __abstract__ = True
    required_any: ClassVar[list[list[str]]] = [["updated_by_admin", "updated_by_admin_uuid"]]

    def __init_subclass__(cls, **kw: object) -> None:
        """Validate the subclass during initialization.

        Args:
            **kw: Additional keyword arguments passed to the subclass.
        """
        cls.validate(cls)
        super().__init_subclass__(**kw)


class UpdatableManagerMixin(EntityAttributeChecker):
    """Mixin for models updatable by managers.

    This mixin ensures that at least one of the manager-related update attributes is present,
    providing tracking of which manager last updated the entity.

    Attributes:
        required_any: Specifies the required manager-related update attributes.
    """

    __abstract__ = True
    required_any: ClassVar[list[list[str]]] = [["updated_by", "updated_by_uuid"]]

    def __init_subclass__(cls, **kw: object) -> None:
        """Validate the subclass during initialization.

        Args:
            **kw: Additional keyword arguments passed to the subclass.
        """
        cls.validate(cls)
        super().__init_subclass__(**kw)


# Level 1: Single mixin composites
class UpdatableEntity(BaseEntity, UpdatableMixin):
    """Base class for entities that support updating timestamps.

    This class extends BaseEntity with update tracking functionality, allowing
    applications to track when records were last modified.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
    """

    __abstract__ = True


class DeletableEntity(BaseEntity, DeletableMixin):
    """Base class for entities that support soft deletion.

    This class extends BaseEntity with soft deletion capability, allowing
    applications to mark records as deleted without physically removing them.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        is_deleted: Flag indicating if the entity is deleted.
    """

    __abstract__ = True


class AdminEntity(BaseEntity, AdminMixin):
    """Base class for entities with admin-related attributes.

    This class extends BaseEntity with tracking of which administrator created
    the entity, supporting audit and accountability requirements.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
    """

    __abstract__ = True


class ManagerEntity(BaseEntity, ManagerMixin):
    """Base class for entities with manager-related attributes.

    This class extends BaseEntity with tracking of which manager created
    the entity, supporting audit and accountability requirements.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        created_by/created_by_uuid: Reference to the manager who created the entity.
    """

    __abstract__ = True


# Level 2: Two mixin composites
class UpdatableDeletableEntity(BaseEntity, UpdatableMixin, DeletableMixin):
    """Base class for entities that support updating timestamps and soft deletion.

    This class combines update tracking and soft deletion capabilities, providing
    a complete history of when records were created, updated, and deleted.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
    """

    __abstract__ = True


class ArchivableEntity(UpdatableEntity, ArchivableMixin):
    """Base class for entities that support archiving.

    This class extends UpdatableEntity with archiving capability, allowing
    applications to mark records as archived and track the original entity.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
    """

    __abstract__ = True


# Level 3: Three mixin composites
class UpdatableAdminEntity(BaseEntity, UpdatableMixin, AdminMixin, UpdatableAdminMixin):
    """Base class for entities updatable by admin with timestamps.

    This class combines creation and update tracking for administrator actions,
    providing a comprehensive audit trail of administrative modifications.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
        updated_by_admin/updated_by_admin_uuid: Reference to the admin who last updated the entity.
    """

    __abstract__ = True


class UpdatableManagerEntity(BaseEntity, UpdatableMixin, ManagerMixin, UpdatableManagerMixin):
    """Base class for entities updatable by managers with timestamps.

    This class combines creation and update tracking for manager actions,
    providing a comprehensive audit trail of management modifications.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        created_by/created_by_uuid: Reference to the manager who created the entity.
        updated_by/updated_by_uuid: Reference to the manager who last updated the entity.
    """

    __abstract__ = True


class ArchivableDeletableEntity(UpdatableDeletableEntity, ArchivableMixin):
    """Base class for entities that support both archiving and soft deletion.

    This class combines archiving and soft deletion capabilities, providing
    a complete history of when records were created, updated, archived, and deleted.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
    """

    __abstract__ = True


# Level 4: Four mixin composites
class UpdatableDeletableAdminEntity(BaseEntity, UpdatableMixin, AdminMixin, UpdatableAdminMixin, DeletableMixin):
    """Base class for entities updatable by admin with timestamps and soft deletion.

    This class combines administrator creation and update tracking with soft deletion,
    providing a complete audit trail throughout the entity's lifecycle.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
        updated_by_admin/updated_by_admin_uuid: Reference to the admin who last updated the entity.
    """

    __abstract__ = True


class UpdatableDeletableManagerEntity(BaseEntity, UpdatableMixin, ManagerMixin, UpdatableManagerMixin, DeletableMixin):
    """Base class for entities updatable by managers with timestamps and soft deletion.

    This class combines manager creation and update tracking with soft deletion,
    providing a complete audit trail throughout the entity's lifecycle.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        created_by/created_by_uuid: Reference to the manager who created the entity.
        updated_by/updated_by_uuid: Reference to the manager who last updated the entity.
    """

    __abstract__ = True


class ArchivableAdminEntity(ArchivableEntity, AdminMixin):
    """Base class for entities Archivable by admin.

    This class extends ArchivableEntity with tracking of which administrator created
    the entity, supporting audit and accountability requirements.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
    """

    __abstract__ = True


class ArchivableManagerEntity(ArchivableEntity, ManagerMixin):
    """Base class for entities Archivable by managers.

    This class extends ArchivableEntity with tracking of which manager created
    the entity, supporting audit and accountability requirements.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
        created_by/created_by_uuid: Reference to the manager who created the entity.
    """

    __abstract__ = True


# Level 5: Five mixin composites
class UpdatableManagerAdminEntity(
    BaseEntity,
    UpdatableMixin,
    ManagerMixin,
    AdminMixin,
    UpdatableManagerMixin,
    UpdatableAdminMixin,
):
    """Base class for entities updatable by both managers and admins with timestamps.

    This class provides comprehensive tracking of entity creation and updates
    by both administrators and managers, supporting complex workflows where
    different user roles interact with the same data.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
        created_by/created_by_uuid: Reference to the manager who created the entity.
        updated_by_admin/updated_by_admin_uuid: Reference to the admin who last updated the entity.
        updated_by/updated_by_uuid: Reference to the manager who last updated the entity.
    """

    __abstract__ = True


class ArchivableManagerAdminEntity(
    ArchivableEntity,
    ManagerMixin,
    AdminMixin,
):
    """Base class for entities Archivable by both managers and admins.

    This class provides comprehensive tracking of entity creation
    by both administrators and managers, supporting complex workflows where
    different user roles interact with the same data.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
        created_by/created_by_uuid: Reference to the manager who created the entity.
    """

    __abstract__ = True


class ArchivableDeletableAdminEntity(ArchivableDeletableEntity, AdminMixin):
    """Base class for entities Archivable and deletable by admin.

    This class combines administrator creation tracking with soft deletion and archiving,
    providing a complete audit trail throughout the entity's lifecycle.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
    """

    __abstract__ = True


class ArchivableDeletableManagerEntity(ArchivableDeletableEntity, ManagerMixin):
    """Base class for entities Archivable and deletable by managers.

    This class combines manager creation tracking with soft deletion and archiving,
    providing a complete audit trail throughout the entity's lifecycle.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
        created_by/created_by_uuid: Reference to the manager who created the entity.
    """

    __abstract__ = True


# Level 6: Six mixin composites
class UpdatableDeletableManagerAdminEntity(
    BaseEntity,
    UpdatableMixin,
    ManagerMixin,
    AdminMixin,
    UpdatableManagerMixin,
    UpdatableAdminMixin,
    DeletableMixin,
):
    """Base class for entities updatable by both managers and admins with timestamps and soft deletion.

    This is the most comprehensive entity class, supporting tracking of creation and
    updates by both administrators and managers, along with soft deletion capability.
    It provides complete accountability for all operations throughout the entity's lifecycle.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
        created_by/created_by_uuid: Reference to the manager who created the entity.
        updated_by_admin/updated_by_admin_uuid: Reference to the admin who last updated the entity.
        updated_by/updated_by_uuid: Reference to the manager who last updated the entity.
    """

    __abstract__ = True


# Level 7: Seven mixin composites
class ArchivableDeletableManagerAdminEntity(
    ArchivableDeletableEntity,
    ManagerMixin,
    AdminMixin,
):
    """Base class for entities Archivable and deletable by both managers and admins.

    This is a comprehensive entity class, supporting tracking of creation
    by both administrators and managers, along with soft deletion and archiving capability.
    It provides complete accountability for all operations throughout the entity's lifecycle.

    Attributes:
        created_at: Timestamp indicating when the entity was created.
        updated_at: Timestamp indicating when the entity was last updated.
        is_deleted: Flag indicating if the entity is deleted.
        is_archived: Flag indicating if the entity is archived.
        origin_uuid: Reference to the original entity.
        created_by_admin/created_by_admin_uuid: Reference to the admin who created the entity.
        created_by/created_by_uuid: Reference to the manager who created the entity.
    """

    __abstract__ = True
