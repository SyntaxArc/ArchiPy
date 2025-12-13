import threading
from collections.abc import Callable
from typing import Any


def singleton_decorator(*, thread_safe: bool = True) -> Callable[[type[Any]], Callable[..., Any]]:
    """A decorator to create thread-safe Singleton classes.

    This decorator ensures that only one instance of a class is created. It supports an optional
    `thread_safe` parameter to control whether thread-safety mechanisms (e.g., locks) should be used.

    Args:
        thread_safe (bool, optional): If True, enables thread-safety for instance creation.
                                      Defaults to True.

    Returns:
        function: A decorator function that can be applied to a class.

    Example:
        To create a Singleton class, apply the `singleton` decorator and optionally specify
        whether thread-safety should be enabled:

        ```python
        @singleton(thread_safe=True)
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
        ```
    """

    def decorator(cls: type[Any]) -> Callable[..., Any]:
        """The inner decorator function that implements the Singleton pattern.

        Args:
            cls: The class to be decorated as a Singleton.

        Returns:
            function: A function that returns the Singleton instance of the class.
        """
        instances = {}  # Stores instances of Singleton classes
        lock: threading.Lock | None = (
            threading.Lock() if thread_safe else None
        )  # Lock for thread-safe instance creation

        def get_instance(*args: Any, **kwargs: Any) -> Any:
            """Create or return the Singleton instance of the class.

            If `thread_safe` is True, a lock is used to ensure that only one instance is created
            even in a multi-threaded environment. If `thread_safe` is False, no locking mechanism
            is used, which may result in multiple instances being created in a multi-threaded context.

            Args:
                *args: Positional arguments to pass to the class constructor.
                **kwargs: Keyword arguments to pass to the class constructor.

            Returns:
                object: The Singleton instance of the class.
            """
            if cls not in instances:
                if thread_safe:
                    if lock is not None:
                        with lock:
                            if cls not in instances:
                                instances[cls] = cls(*args, **kwargs)
                else:
                    instances[cls] = cls(*args, **kwargs)
            return instances[cls]

        return get_instance

    return decorator
