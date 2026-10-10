"""ScyllaDB adapter module.

This module provides adapters for interacting with ScyllaDB/Cassandra databases
using the Ports & Adapters pattern.
"""

from archipy.adapters.scylladb.adapters import AsyncScyllaDBAdapter, ScyllaDBAdapter
from archipy.adapters.scylladb.ports import AsyncScyllaDBPort, ScyllaDBPort

__all__ = [
    "AsyncScyllaDBAdapter",
    "AsyncScyllaDBPort",
    "ScyllaDBAdapter",
    "ScyllaDBPort",
]
