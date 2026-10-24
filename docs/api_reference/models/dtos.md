---
title: DTOs
description: API reference for ArchiPy Data Transfer Objects.
---

# DTOs

The `models/dtos` subpackage contains Pydantic `BaseModel` data transfer objects used for API request/response shapes,
pagination, sorting, search, and email payloads.

## Base DTOs

Base DTO classes providing common fields and validators inherited by domain-specific DTOs.

::: archipy.models.dtos.base_dtos
options:
show_root_toc_entry: false
heading_level: 3

## Base Protobuf DTO

Base DTO class for Protobuf-backed data transfer objects, bridging gRPC and Pydantic models.

::: archipy.models.dtos.base_protobuf_dto
options:
show_root_toc_entry: false
heading_level: 3

## Pagination DTO

DTOs for pagination input and output, including page number, page size, and total count fields.

::: archipy.models.dtos.pagination_dto
options:
show_root_toc_entry: false
heading_level: 3

## Sort DTO

DTOs for expressing sort order in list/search requests.

::: archipy.models.dtos.sort_dto
options:
show_root_toc_entry: false
heading_level: 3

## Search Input DTO

DTO for structured search input combining filter, sort, and pagination parameters.

::: archipy.models.dtos.search_input_dto
options:
show_root_toc_entry: false
heading_level: 3

## Search Output DTO

Base DTOs for paged search outputs, with `total_count` and the computed `total_count_estimated`.

::: archipy.models.dtos.search_output_dto
options:
show_root_toc_entry: false
heading_level: 3

## Range DTOs

DTOs for expressing numeric and date range filters in queries.

::: archipy.models.dtos.range_dtos
options:
show_root_toc_entry: false
heading_level: 3

## Email DTOs

DTOs for composing email messages including recipients, subject, body, and attachments.

::: archipy.models.dtos.email_dtos
options:
show_root_toc_entry: false
heading_level: 3

## Rate Limit Window DTO

DTO for a single rate-limit tier: maximum calls within a time window.

::: archipy.models.dtos.rate_limit_window_dto
options:
show_root_toc_entry: false
heading_level: 3


## RediSearch DTOs

DTOs for RediSearch index schemas, document upserts, queries, aggregations, and normalized search results.

::: archipy.models.dtos.redis.search
options:
show_root_toc_entry: false
heading_level: 3

## Keycloak DTOs

Pydantic DTOs for the Keycloak adapter: admin API representations (users, groups, roles, clients, organizations,
authorization, authentication flows), UMA payloads, and OpenID Connect token, userinfo and claims responses. Response
DTOs keep unknown fields; request DTOs reject them.

::: archipy.models.dtos.keycloak
options:
show_root_toc_entry: false
heading_level: 3

::: archipy.models.dtos.keycloak.base
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.auth_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.token_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.user_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.group_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.role_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.client_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.client_scope_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.protocol_mapper_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.organization_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.identity_provider_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.realm_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.authz_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.authz_policy_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.auth_flow_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.authenticator_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.uma_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.event_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.key_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.certificate_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.client_policy_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.client_initial_access_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.attack_detection_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.partial_import_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.session_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.user_profile_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.management_permission_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.client_evaluation_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.component_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.common_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.authz_evaluation_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.authzen_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.protocol_mapper_config_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.required_action_dtos
options:
show_root_toc_entry: false
heading_level: 4

::: archipy.models.dtos.keycloak.token_exchange_dtos
options:
show_root_toc_entry: false
heading_level: 4
