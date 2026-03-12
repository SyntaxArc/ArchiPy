---
title: "3.x Changelog"
description: "Release history for ArchiPy 3.x series"
---

# 3.x Changelog

[↑ All versions](../index.md)

| Version               | Date       | Summary                                                                                         |
|-----------------------|------------|-------------------------------------------------------------------------------------------------|
| [3.15.3](3.15.3.md)   | 2025-12-02 | Lazy Import for SQLAlchemy Decorators: Changed SQLAlchemy decorators to use lazy imports via... |
| [3.15.2](3.15.2.md)   | 2025-12-02 | Conditional Insert Support: Added `if_not_exists` parameter to `insert()` method in ScyllaDB... |
| [3.15.1](3.15.1.md)   | 2025-11-30 | Retry Policies: Added configurable retry policies for handling transient failures in ScyllaD... |
| [3.15.0](3.15.0.md)   | 2025-11-29 | ScyllaDB/Cassandra Adapter: Implemented comprehensive adapter for ScyllaDB and Apache Cassan... |
| [3.14.4](3.14.4.md)   | 2025-11-20 | Comprehensive Dependency Synchronization: Updated multiple core dependencies to latest versi... |
| [3.14.3](3.14.3.md)   | 2025-11-11 | Removed Invalid Retry on Timeout Configuration: Fixed Redis adapter configuration by removin... |
| [3.14.2](3.14.2.md)   | 2025-11-06 | Tag-Based Selective Container Startup: Implemented intelligent container startup based on fe... |
| [3.14.1](3.14.1.md)   | 2025-10-30 | ReDoc Configuration Field Name Correction: Fixed typo in FastAPI configuration field name       |
| [3.14.0](3.14.0.md)   | 2025-10-26 | gRPC App Creation: Added comprehensive gRPC application creation utilities for both sync and... |
| [3.13.10](3.13.10.md) | 2025-10-20 | Comprehensive Dependency Synchronization: Updated multiple core dependencies to latest versi... |
| [3.13.9](3.13.9.md)   | 2025-10-15 | Enhanced Client Reuse: Improved Elastic APM client initialization to prevent duplicate clien... |
| [3.13.8](3.13.8.md)   | 2025-10-15 | Redis Cluster Parameter Standardization: Aligned Redis cluster configuration with redis-py l... |
| [3.13.7](3.13.7.md)   | 2025-10-13 | Core Dependencies: Updated key dependencies to latest versions for improved security and per... |
| [3.13.6](3.13.6.md)   | 2025-01-15 | Core Framework Updates: Updated key dependencies to latest compatible versions for improved ... |
| [3.13.5](3.13.5.md)   | 2025-10-08 | Comprehensive Dependency Synchronization: Updated all dependencies to latest compatible vers... |
| [3.13.4](3.13.4.md)   | 2025-10-07 | Comprehensive Dependency Synchronization: Updated all dependencies to latest compatible vers... |
| [3.13.3](3.13.3.md)   | 2025-09-30 | Comprehensive Example Documentation Refactor: Updated all 17 example files to follow modern ... |
| [3.13.2](3.13.2.md)   | 2025-09-30 | MkDocs Configuration Reorganization: Restructured MkDocs configuration for improved build pe... |
| [3.13.1](3.13.1.md)   | 2025-09-30 | Core Dependencies: Updated multiple core dependencies for improved security and performance     |
| [3.13.0](3.13.0.md)   | 2025-09-21 | Redis Cluster Integration: Added comprehensive Redis Cluster support for distributed caching... |
| [3.12.0](3.12.0.md)   | 2025-09-21 | Schedule Management Methods: Added comprehensive schedule management capabilities to Tempora... |
| [3.11.1](3.11.1.md)   | 2025-09-06 | Wait Until Stopped Method: Added `wait_until_stopped()` method to Temporal WorkerHandle class   |
| [3.11.0](3.11.0.md)   | 2025-09-04 | Comprehensive Temporal Integration: Added complete Temporal workflow orchestration support      |
| [3.10.0](3.10.0.md)   | 2025-09-04 | Sentry Support in gRPC Trace Interceptors: Enhanced gRPC trace interceptors with dual APM su... |
| [3.9.0](3.9.0.md)     | 2025-09-04 | Pure Python APM Tracing: Added `@capture_transaction` and `@capture_span` decorators for pur... |
| [3.8.1](3.8.1.md)     | 2025-09-04 | Elasticsearch Version Bump: Updated Elasticsearch Docker image from 9.1.2 to 9.1.3 in test c... |
| [3.8.0](3.8.0.md)     | 2025-08-21 | Poetry to UV Migration: Migrated from Poetry to UV for improved performance and modern toolc... |
| [3.7.0](3.7.0.md)     | 2025-08-16 | Index Existence Check: Added `index_exists` method to Elasticsearch adapters for improved in... |
| [3.6.1](3.6.1.md)     | 2025-08-11 | Bandit Security Tool: Added comprehensive security vulnerability scanning to the development... |
| [3.6.0](3.6.0.md)     | 2025-07-29 | Centralized Exception Handling: Implemented comprehensive gRPC server exception interceptors... |
| [3.5.2](3.5.2.md)     | 2025-07-28 | Password Secret Value Extraction: Fixed critical authentication issue in Elasticsearch adapt... |
| [3.5.1](3.5.1.md)     | 2025-07-28 | Status Code Name Mismatch: Fixed critical issue in FastAPIExceptionHandler where `http_statu... |
| [3.5.0](3.5.0.md)     | 2025-07-26 | BaseProtobufDTO: Added new base class for Data Transfer Objects that can be converted to and... |
| [3.4.5](3.4.5.md)     | 2025-07-24 | Improved Readability: Enhanced ElasticsearchAPMConfig size fields to use human-readable stri... |
| [3.4.4](3.4.4.md)     | 2025-07-17 | Import Safety: Added robust gRPC import handling with try/except blocks to prevent import er... |
| [3.4.3](3.4.3.md)     | 2025-07-17 | Admin Mode Control: Implemented `IS_ADMIN_MODE_ENABLED` configuration flag to control Keyclo... |
| [3.4.2](3.4.2.md)     | 2025-07-17 | Import Error Resolution: Fixed critical import errors that were preventing proper module ini... |
| [3.4.1](3.4.1.md)     | 2025-07-07 | Import Error Fix: Resolved import error issues that were affecting module loading and depend... |
| [3.4.0](3.4.0.md)     | 2025-06-29 | Async gRPC Server Interceptors: Added comprehensive async gRPC server interceptors with enha... |
| [3.3.1](3.3.1.md)     | 2025-06-12 | Enhanced error handling: Added comprehensive custom error classes and centralized exception ... |
| [3.3.0](3.3.0.md)     | 2025-06-09 | New Elasticsearch adapter: Added comprehensive Elasticsearch integration with full search an... |
| [3.2.7](3.2.7.md)     | 2025-01-06 | Enhanced query result handling: Added `has_multiple_entities` parameter to search query meth... |
| [3.2.6](3.2.6.md)     | 2025-01-06 | Optimized search query execution: Refactored SQLAlchemy query execution method to use `fetch... |
| [3.2.5](3.2.5.md)     | 2025-01-06 | Enhanced changelog generation script: Significantly improved the changelog generation proces... |
| [3.2.4](3.2.4.md)     | 2025-01-27 | Fixed atomic transactions feature test error handling expectations:                             |
| [3.2.3](3.2.3.md)     | 2025-01-24 | Fix using "IS_ENABLED" instead wrong variable "ENABLED" in elastic ap… by @majasemzadeh...      |
| [3.2.2](3.2.2.md)     | 2025-05-24 | Enhanced timestamp handling in SQLAlchemy base entities:                                        |
| [3.2.1](3.2.1.md)     | 2025-05-20 | Enhanced Elastic APM configuration and integration:                                             |
| [3.2.0](3.2.0.md)     | 2025-05-20 | Added and refactored methods for creating realms, clients, and client roles in Keycloak...      |
| [3.1.1](3.1.1.md)     | 2025-05-17 | Enhanced project documentation                                                                  |
| [3.1.0](3.1.0.md)     | 2025-05-15 | Implemented Parsian Internet Payment Gateway adapter                                            |
| [3.0.1](3.0.1.md)     | 2025-04-27 | Fixed import error in module dependencies                                                       |
| [3.0.0](3.0.0.md)     | 2025-04-27 | Refactor StarRocks driver integration                                                           |
