"""Helpers for config sections that move flat fields into nested groups."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import BaseModel


def deprecated_flat_message(section: str, flat_name: str, group: str, field: str) -> str:
    """Return the deprecation message of a flat setting that moved into a nested group.

    Args:
        section: Config section name, for example ``"VAULT"``.
        flat_name: Old flat field name, for example ``"APPROLE_ROLE_ID"``.
        group: New group name, for example ``"APPROLE"``.
        field: Field name inside the group, for example ``"ROLE_ID"``.

    Returns:
        The message to pass to ``Field(deprecated=...)``.
    """
    return f"Use {section}.{group}.{field} instead; {section}.{flat_name} will be removed in 6.0.0"


def fold_flat_fields(
    owner: BaseModel,
    group: str,
    group_type: type[BaseModel],
    flat_to_field: Mapping[str, str],
) -> None:
    """Copy deprecated flat settings into a nested group.

    Only flat fields the user set explicitly are used. Declare them with ``Field(deprecated=...)``: reading them here
    makes pydantic emit one ``DeprecationWarning`` per field. A value already set on the group wins. The group is
    created when it is ``None``. Call this from a ``model_validator(mode="after")`` of the section.

    Args:
        owner: The section model that holds the flat fields and the group.
        group: Attribute name of the group on ``owner``.
        group_type: Model class of the group.
        flat_to_field: Maps each flat field name to its field name inside the group.
    """
    used = sorted(name for name in flat_to_field if name in owner.model_fields_set)
    if not used:
        return
    current: BaseModel | None = getattr(owner, group)
    values: dict[str, Any] = current.model_dump(exclude_unset=True) if current is not None else {}
    for name in used:
        values.setdefault(flat_to_field[name], getattr(owner, name))
    object.__setattr__(owner, group, group_type(**values))
