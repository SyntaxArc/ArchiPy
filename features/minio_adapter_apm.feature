# features/minio_operations.feature
@needs-minio @needs-apm-server @needs-apm-collector
Feature: MinIO Operations Testing with Elastic APM
  As a developer
  I want to test MinIO storage operations
  So that I can ensure reliable object storage functionality

  Background:
    Given a configured MinIO adapter

  Scenario Outline: MinIO adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I upload and download an object through the MinIO adapter
    Then Elastic APM Server should store a span of type "external" with subtype "aws-api"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
