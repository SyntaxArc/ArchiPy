"""Optional FastAPI imports for the application bootstrap helpers."""

from typing import TYPE_CHECKING

try:
    from fastapi import FastAPI
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from starlette.middleware.cors import CORSMiddleware
except ImportError:
    # Static types describe the interface with the extra installed.
    if TYPE_CHECKING:
        raise
    FASTAPI_APP = False
    FastAPI = None
    GZipMiddleware = None
    HTTPSRedirectMiddleware = None
    TrustedHostMiddleware = None
    CORSMiddleware = None
else:
    FASTAPI_APP = True

__all__ = [
    "FASTAPI_APP",
    "CORSMiddleware",
    "FastAPI",
    "GZipMiddleware",
    "HTTPSRedirectMiddleware",
    "TrustedHostMiddleware",
]
