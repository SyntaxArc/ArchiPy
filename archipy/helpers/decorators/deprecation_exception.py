from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from archipy.models.errors import DeprecationError
from archipy.models.types.language_type import LanguageType

# Define type variables for the decorator
P = ParamSpec("P")
R = TypeVar("R")

# Define a type variable for the return type of the decorated class
T = TypeVar("T", bound=type[Any])


def method_deprecation_error(
    operation: str | None = None,
    lang: LanguageType = LanguageType.EN,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that raises a DeprecationError when the decorated method is called.

    This decorator is used to mark methods as deprecated and immediately prevent
    their use by raising a DeprecationError when they are called. This is stricter
    than a warning and ensures deprecated methods cannot be used.

    Args:
        operation (str, optional): The name of the operation that is deprecated.
            Defaults to the name of the decorated method.
        lang (LanguageType): The language for the error message (default: "en").

    Returns:
        Callable: The decorated method that raises a DeprecationException.

    Example:
        To use this decorator, apply it to a method:

        ```python
        class MyClass:
            @method_deprecation_error(operation="old_method", lang=LanguageType.EN)
            def old_method(self):
                return "This is the old method."


        # Calling the method will raise a DeprecationException
        obj = MyClass()
        result = obj.old_method()
        ```

        Output:
        ```
        DeprecationException: This operation is deprecated and will be removed in a future version.
        Operation: old_method
        ```
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Capture function name before wrapping - use getattr for type safety
        func_name = getattr(func, "__name__", "unknown")

        @wraps(func)
        def wrapper(*_args: P.args, **_kwargs: P.kwargs) -> R:
            operation_name = operation if operation is not None else func_name
            raise DeprecationError(deprecated_feature=operation_name, lang=lang)

        return wrapper

    return decorator


def class_deprecation_error(operation: str | None = None, lang: LanguageType = LanguageType.FA) -> Callable[[T], T]:
    """A decorator that raises a DeprecationException when the decorated class is instantiated.

    Args:
        operation (str, optional): The name of the operation that is deprecated.
            Defaults to the name of the decorated class.
        lang (str): The language for the error message (default: "fa").

    Returns:
        Callable: The decorated class that raises a DeprecationException.

    Example:
        To use this decorator, apply it to a class:

        ```python
        @class_deprecation_error(operation="OldClass", lang="en")
        class OldClass:
            def __init__(self):
                pass


        # Instantiating the class will raise a DeprecationException
        obj = OldClass()
        ```

        Output:
        ```
        DeprecationException: This operation is deprecated and will be removed in a future version.
        Operation: OldClass
        ```
    """

    def decorator(cls: T) -> T:
        def new_init(_self: Any, *_args: Any, **_kwargs: Any) -> None:
            operation_name = operation if operation is not None else cls.__name__
            raise DeprecationError(deprecated_feature=operation_name, lang=lang)

        cls.__init__ = new_init
        return cls

    return decorator
