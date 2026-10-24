"""Keycloak-related data transfer objects (kept for backward compatibility).

The DTOs now live in :mod:`archipy.models.dtos.keycloak`.
"""

from archipy.models.dtos.keycloak.auth_dtos import ActorDTO, AuthenticatedUserDTO

__all__ = ["ActorDTO", "AuthenticatedUserDTO"]
