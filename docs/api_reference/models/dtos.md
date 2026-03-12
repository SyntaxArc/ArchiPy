# DTOs

The `models/dtos` subpackage contains Pydantic `BaseModel` data transfer objects used for API request/response shapes, pagination, sorting, search, and email payloads.

## Base DTOs

Base DTO classes providing common fields and validators inherited by domain-specific DTOs.

::: archipy.models.dtos.base_dtos
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Base Protobuf DTO

Base DTO class for Protobuf-backed data transfer objects, bridging gRPC and Pydantic models.

::: archipy.models.dtos.base_protobuf_dto
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Pagination DTO

DTOs for pagination input and output, including page number, page size, and total count fields.

::: archipy.models.dtos.pagination_dto
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Sort DTO

DTOs for expressing sort order in list/search requests.

::: archipy.models.dtos.sort_dto
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Search Input DTO

DTO for structured search input combining filter, sort, and pagination parameters.

::: archipy.models.dtos.search_input_dto
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Range DTOs

DTOs for expressing numeric and date range filters in queries.

::: archipy.models.dtos.range_dtos
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Email DTOs

DTOs for composing email messages including recipients, subject, body, and attachments.

::: archipy.models.dtos.email_dtos
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## FastAPI Exception Response DTO

DTO representing the standardized error response body returned by FastAPI exception handlers.

::: archipy.models.dtos.fastapi_exception_response_dto
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3
