"""Singleton metaclass helpers."""

import threading
from typing import TYPE_CHECKING, ClassVar, cast

if TYPE_CHECKING:
    from collections.abc import Hashable


# Define type constants for explicit typing
SingletonInstance = object
ClassDict = dict[str, object]
ClassBases = tuple[type, ...]


class Singleton(type):
    """A thread-safe Singleton metaclass that ensures only one instance of a class is created.

    This metaclass can be used to create Singleton classes. It supports an optional `thread_safe`
    parameter to control whether thread-safety mechanisms (e.g., locks) should be used.

    Attributes:
        _instances (dict): A dictionary to store instances of Singleton classes.
        _lock (threading.RLock): A reentrant lock to ensure thread-safe instance creation; a singleton whose
            constructor creates another singleton does not deadlock.

    Example:
        To create a Singleton class, use the `Singleton` metaclass and optionally specify
        whether thread-safety should be enabled:

        ```python
        class MySingletonClass(metaclass=Singleton, thread_safe=True):
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

    _instances: ClassVar[dict[type, SingletonInstance]] = {}  # Stores instances of Singleton classes
    _lock: ClassVar[threading.RLock] = threading.RLock()  # Lock for thread-safe instance creation
    _keyed_instances: ClassVar[dict[tuple[type, Hashable], SingletonInstance]] = {}  # Instances of keyed singletons

    def __new__(
        cls,
        name: str,
        bases: ClassBases,
        dct: ClassDict,
        **kwargs: object,
    ) -> type:
        """Create a new Singleton metaclass instance.

        Args:
            name (str): The name of the class.
            bases (tuple): The base classes of the class.
            dct (dict): The namespace containing the class attributes.
            **kwargs: Additional keyword arguments, including `thread_safe`.

        Returns:
            type: A new metaclass instance.
        """
        # Extract the `thread_safe` parameter from kwargs
        thread_safe = kwargs.pop("thread_safe", True)
        # Create the new class
        new_class = super().__new__(cls, name, bases, dct, **kwargs)
        # Store thread_safe as an attribute using setattr to avoid linting errors
        setattr(new_class, "__thread_safe", thread_safe)
        return new_class

    def __call__[T](cls: type[T], *args: object, **kwargs: object) -> T:
        """Create or return the Singleton instance of the class.

        If `thread_safe` is True, a lock is used to ensure that only one instance is created
        even in a multi-threaded environment. If `thread_safe` is False, no locking mechanism
        is used, which may result in multiple instances being created in a multi-threaded context.

        A class that defines a ``_singleton_key`` classmethod gets one instance per key instead of one per class.
        The method receives the constructor arguments and returns a hashable key, so ``Manager(config_a)`` and
        ``Manager(config_b)`` are two instances while repeated ``Manager(config_a)`` calls return the same one.

        Args:
            *args: Positional arguments to pass to the class constructor.
            **kwargs: Keyword arguments to pass to the class constructor.

        Returns:
            object: The Singleton instance of the class.
        """
        # ``cls`` is annotated as ``type[T]`` so callers get their own instance type; it is a ``Singleton`` at runtime.
        meta = cast("Singleton", cls)
        key_function = getattr(cls, "_singleton_key", None)
        if key_function is not None:
            instance_key = (cls, key_function(*args, **kwargs))
            if instance_key not in meta._keyed_instances:
                with meta._lock:
                    if instance_key not in meta._keyed_instances:
                        meta._keyed_instances[instance_key] = super(Singleton, meta).__call__(*args, **kwargs)
            # The stores are keyed by the class, so the stored value is an instance of ``cls``.
            return cast("T", meta._keyed_instances[instance_key])
        if cls not in meta._instances:
            if getattr(cls, "__thread_safe", True):
                with meta._lock:
                    if cls not in meta._instances:
                        meta._instances[cls] = super(Singleton, meta).__call__(*args, **kwargs)
            else:
                # Two racing threads may both construct, but every caller receives the first stored instance
                meta._instances.setdefault(cls, super(Singleton, meta).__call__(*args, **kwargs))
        return cast("T", meta._instances[cls])
