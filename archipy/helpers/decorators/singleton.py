"""Singleton decorator helpers."""

from __future__ import annotations

import threading
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager


def singleton_decorator[T: type[Any]](*, thread_safe: bool = True) -> Callable[[T], T]:
    """A decorator to create thread-safe Singleton classes.

    This decorator ensures that only one instance of a class is created. The decorated name
    is still the class itself, so ``isinstance``, subclassing and class-level attributes keep
    working. Constructor arguments passed after the first instantiation are ignored.

    Args:
        thread_safe (bool, optional): If True, enables thread-safety for instance creation.
                                      Defaults to True.

    Returns:
        function: A decorator function that can be applied to a class.

    Example:
        To create a Singleton class, apply the `singleton_decorator` and optionally specify
        whether thread-safety should be enabled:

        ```python
        @singleton_decorator(thread_safe=True)
        class MySingletonClass:
            def __init__(self, value):
                self.value = value


        # Create instances of MySingletonClass
        instance1 = MySingletonClass(10)
        instance2 = MySingletonClass(20)

        # Verify that both instances are the same
        print(instance1.value)  # Output: 10
        print(instance2.value)  # Output: 10
        print(instance1 is instance2)  # Output: True
        print(isinstance(instance1, MySingletonClass))  # Output: True
        ```
    """

    def decorator(cls: T) -> T:
        """Patch the class so that it only ever builds and initializes one instance.

        Args:
            cls: The class to be decorated as a Singleton.

        Returns:
            The same class, now limited to a single instance per (sub)class.
        """
        instances: dict[type, Any] = {}
        initialized: set[type] = set()
        # Without thread safety a no-op context manager replaces the lock
        lock: AbstractContextManager[Any] = threading.RLock() if thread_safe else nullcontext()
        original_new = cls.__new__
        original_init = cls.__init__

        def singleton_new(klass: type, *args: Any, **kwargs: Any) -> Any:
            if klass not in instances:
                with lock:
                    if klass not in instances:
                        if original_new is object.__new__:
                            instances[klass] = original_new(klass)
                        else:
                            instances[klass] = original_new(klass, *args, **kwargs)
            return instances[klass]

        def singleton_init(self: Any, *args: Any, **kwargs: Any) -> None:
            klass = type(self)
            if klass not in initialized:
                with lock:
                    if klass not in initialized:
                        original_init(self, *args, **kwargs)
                        initialized.add(klass)

        cls.__new__ = singleton_new  # type: ignore[assignment]
        cls.__init__ = singleton_init  # type: ignore[misc]
        return cls

    return decorator
