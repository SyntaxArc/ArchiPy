# DTOs

The `models/dtos` subpackage contains Pydantic `BaseModel` data transfer objects used for API request/response shapes, pagination, sorting, search, and email payloads.

## base_dtos

Base DTO classes providing common fields and validators inherited by domain-specific DTOs.

::: archipy.models.dtos.base_dtos
    options:
      show_root_heading: true
      show_source: true

## base_protobuf_dto

Base DTO class for Protobuf-backed data transfer objects, bridging gRPC and Pydantic models.

::: archipy.models.dtos.base_protobuf_dto
    options:
      show_root_heading: true
      show_source: true

## pagination_dto

DTOs for pagination input and output, including page number, page size, and total count fields.

::: archipy.models.dtos.pagination_dto
    options:
      show_root_heading: true
      show_source: true

## sort_dto

DTOs for expressing sort order in list/search requests.

::: archipy.models.dtos.sort_dto
    options:
      show_root_heading: true
      show_source: true

## search_input_dto

DTO for structured search input combining filter, sort, and pagination parameters.

::: archipy.models.dtos.search_input_dto
    options:
      show_root_heading: true
      show_source: true

## range_dtos

DTOs for expressing numeric and date range filters in queries.

::: archipy.models.dtos.range_dtos
    options:
      show_root_heading: true
      show_source: true

## email_dtos

DTOs for composing email messages including recipients, subject, body, and attachments.

::: archipy.models.dtos.email_dtos
    options:
      show_root_heading: true
      show_source: true

## fastapi_exception_response_dto

DTO representing the standardized error response body returned by FastAPI exception handlers.

::: archipy.models.dtos.fastapi_exception_response_dto
    options:
      show_root_heading: true
      show_source: true
