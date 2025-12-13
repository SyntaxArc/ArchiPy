import warnings
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

# Define type variables for the decorator
P = ParamSpec("P")
R = TypeVar("R")
# Define a type variable for the return type of the decorated class
T = TypeVar("T", bound=type[Any])


def method_deprecation_warning(message: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A decorator that issues a deprecation warning when the decorated method is called.

    Args:
        message (str, optional): The deprecation message to display when the method is called.
            Defaults to "This method is deprecated and will be removed in a future version."

    Returns:
        Callable: The decorated method that issues a deprecation warning.

    Example:
        To use this decorator, apply it to a method:

        ```python
        class MyClass:
            @method_deprecation_warning("This method is deprecated and will be removed in a future version.")
            def old_method(self):
                return "This is the old method."


        # Calling the method will issue a deprecation warning
        obj = MyClass()
        result = obj.old_method()
        ```

        Output:
        ```
        DeprecationWarning: This method is deprecated and will be removed in a future version.
        This is the old method.
        ```
    """
    default_message = "This method is deprecated and will be removed in a future version."
    final_message = message if message is not None else default_message

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            warnings.warn(final_message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        # @wraps preserves the function signature, making wrapper compatible with the original function
        wrapper.__wrapped__ = func
        return wrapper

    return decorator


def class_deprecation_warning(message: str | None = None) -> Callable[[T], T]:
    """A decorator that issues a deprecation warning when the decorated class is instantiated.

    Args:
        message (str, optional): The deprecation message to display when the class is instantiated.
            Defaults to "This class is deprecated and will be removed in a future version."

    Returns:
        Callable: The decorated class that issues a deprecation warning.

    Example:
        To use this decorator, apply it to a class:

        ```python
        @class_deprecation_warning("This class is deprecated and will be removed in a future version.")
        class OldClass:
            def __init__(self):
                pass


        # Instantiating the class will issue a deprecation warning
        obj = OldClass()
        ```

        Output:
        ```
        DeprecationWarning: This class is deprecated and will be removed in a future version.
        ```
    """
    default_message = "This class is deprecated and will be removed in a future version."
    final_message = message if message is not None else default_message

    def decorator(cls: T) -> T:
        original_init = cls.__init__

        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            warnings.warn(final_message, DeprecationWarning, stacklevel=2)
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return decorator
