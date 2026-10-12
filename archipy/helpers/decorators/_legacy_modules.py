"""Import the deprecated module paths (``decorators.retry`` and friends) before any public name is bound.

Importing a submodule sets an attribute with its name on the package. The suffix-less decorators
(``retry``, ``timeout``, ...) share those names, so the shims must be loaded first and the
decorators bound afterwards for the decorators to win.
"""

import importlib

for _shim in ("cache", "grpc_rate_limit", "retry", "singleton", "sqlalchemy_atomic", "timeout", "timing"):
    importlib.import_module(f"archipy.helpers.decorators.{_shim}")
