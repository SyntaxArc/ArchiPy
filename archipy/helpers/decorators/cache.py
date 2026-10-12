"""Deprecated import path; use ``archipy.helpers.decorators`` and ``ttl_cache`` instead."""

from .ttl_caching import CachedFunction, ttl_cache_decorator

__all__ = ["CachedFunction", "ttl_cache_decorator"]
