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
