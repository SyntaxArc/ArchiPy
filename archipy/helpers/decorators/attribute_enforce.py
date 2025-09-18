from collections.abc import Callable


def enforce_attributes[T](attrs: tuple[tuple[tuple[str, ...], ...], ...]) -> Callable[[type[T]], type[T]]:
    """A decorator that checks existence of given attributes on a class.

    Args:
        attrs (`tuple[tuple[tuple[str, ...], ...], ...]`): A tuple of tuples of tuples of attribute names, of which one
            shall exist as class variable or annotation.

    Returns:
        type: The validated class.

    Raises:
        AttributeError: if one or more of the required attributes don't exist on the class.

    Example:
        To use this decorator, apply it to a class.

        ```python
        manager_attrs = ("created_by", "created_by_uuid")
        admin_attrs = ("created_by_admin", "created_by_admin_uuid")

        @ensure_attrs((admin_attrs, manager_attrs))
        class CustomType:
            created_by: UUID
            created_by_admin_uuid: UUID
        ```
    """

    def validator(kls: type[T]) -> type[T]:
        if "__annotations__" in (existing_attrs := set(vars(kls).keys())):
            existing_attrs.update(vars(kls)["__annotations__"])
        for category in attrs:
            for group in category:
                if len(existing_attrs.intersection(group)) == 0:
                    error_message = f"none of {group} is present on {kls.__name__}"
                    raise AttributeError(error_message)
        return kls

    return validator
