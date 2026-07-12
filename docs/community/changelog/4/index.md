---
title: "4.x Changelog"
description: "Release history for ArchiPy 4.x series"
---

# 4.x Changelog

[↑ All versions](../index.md)

| Version             | Date       | Summary                                                                                         |
|---------------------|------------|-------------------------------------------------------------------------------------------------|
| [4.13.2](4.13.2.md) | 2026-07-12 | FastAPI nested router metric fix, ScyllaDB NetworkTopologyStrategy default, dependency bumps    |
| [4.13.1](4.13.1.md) | 2026-06-30 | Temporal SDK 1.29 config expansion for client connection, worker tuning, and retry policies     |
| [4.13.0](4.13.0.md) | 2026-06-30 | Keycloak group management, Redis flushdb, RESP3 protocol config, sentinel auth, and cluster tests   |
| [4.12.1](4.12.1.md) | 2026-06-23 | FastAPI 0.138+ compatibility, Caveman agent skills, and dependency pin updates                |
| [4.12.0](4.12.0.md) | 2026-06-20 | MinIO TTL/lifecycle, object tags, batch deletion, existence checks, and versioning support      |
| [4.11.1](4.11.1.md) | 2026-06-18 | FastAPI compatibility pin to <0.137, removed parallel behave settings, docs alignment           |
| [4.11.0](4.11.0.md) | 2026-06-18 | MinIO stream upload/download APIs, IPG DTO extraction, and FastAPI large-file upload tests      |
| [4.10.2](4.10.2.md) | 2026-06-15 | httpx2 HTTP client migration, gRPC/app-utils fixes, and dependency updates                      |
| [4.10.1](4.10.1.md) | 2026-05-31 | FastAPI APM middleware ordering fix, Redis type-hint refactor, and dependency updates           |
| [4.10.0](4.10.0.md) | 2026-05-18 | Batch UMA permission checks for Keycloak, shared adapter instances, and auth pipeline refactor  |
| [4.9.3](4.9.3.md)   | 2026-05-13 | Lazy Redis client initialization in rate limiter, `__future__` typing, and dependency updates   |
| [4.9.2](4.9.2.md)   | 2026-05-12 | Fix graceful handling of missing TransactionDetail in Saman payment adapters                    |
| [4.9.1](4.9.1.md)   | 2026-05-12 | ScyllaDB async callback fix, driver upgrades (scylla-driver 3.29.10), and dependency updates    |
| [4.9.0](4.9.0.md)   | 2026-05-09 | Null commit and batch consume support for Kafka adapters                                        |
| [4.8.1](4.8.1.md)   | 2026-05-06 | Prometheus utils class refactor, stricter ScyllaDB CQL validation, and dependency refresh       |
| [4.8.0](4.8.0.md)   | 2026-05-03 | Async tracing decorators, improved error handling, gRPC interceptor fixes                       |
| [4.7.1](4.7.1.md)   | 2026-05-03 | `TracingUtils` class, extended Sentry config, consolidated error handling tests                 |
| [4.7.0](4.7.0.md)   | 2026-04-28 | MinIO copy_object method, advanced CORS configuration, and comprehensive tests                  |
| [4.6.0](4.6.0.md)   | 2026-04-27 | Parsian and Saman IPG async adapters, port interface extraction, and dependency updates         |
| [4.5.0](4.5.0.md)   | 2026-04-27 | Saman Shaparak adapter, DatetimeUtils caching refactor, and dependency updates                  |
| [4.4.2](4.4.2.md)   | 2026-04-15 | asyncmy to asyncmy2 migration, dev dependency refresh, and test container image updates         |
| [4.4.1](4.4.1.md)   | 2026-04-06 | Dependency refresh, regenerated lockfile, and typing cleanups for Keycloak and atomic decorator |
| [4.4.0](4.4.0.md)   | 2026-03-13 | Async Kafka producer and consumer adapters, async BDD step refactor                             |
| [4.3.6](4.3.6.md)   | 2026-03-13 | SQLAlchemy filter type expansion, docs overhaul, CI pipeline fixes                              |
| [4.3.5](4.3.5.md)   | 2026-03-10 | SSL Config Typing: Improved type safety and optional-field handling for SSL configuration in... |
| [4.3.4](4.3.4.md)   | 2026-02-24 | BaseError `__str__` Enhancement: Improved string representation to expose full error context    |
| [4.3.3](4.3.3.md)   | 2026-02-23 | Type-Safe Field References: Reverted the experimental type-safe field references feature        |
| [4.3.1](4.3.1.md)   | 2026-02-22 | Boto3 Migration: Migrated MinIO adapter from minio library to boto3                             |
| [4.3.0](4.3.0.md)   | 2026-02-22 | Prometheus Utilities: Added shared Prometheus server management module                          |
| [4.2.0](4.2.0.md)   | 2026-02-21 | Metric Interceptors: Enhanced Prometheus metrics collection across frameworks                   |
| [4.1.0](4.1.0.md)   | 2026-02-09 | Organization Management: Implemented comprehensive organization management functionality        |
| [4.0.4](4.0.4.md)   | 2026-01-31 | Enhanced Exception Handling: Improved exception handling in SQLAlchemy atomic decorators        |
| [4.0.3](4.0.3.md)   | 2026-01-24 | Add PostgreSQL and SQLite support for atomic transaction tests                                  |
| [4.0.2](4.0.2.md)   | 2025-12-11 | Broadened Ruff configuration (additional ignores, per-file overrides, relaxed limits) a...      |
| [4.0.1](4.0.1.md)   | 2025-12-10 | Comprehensive Cache Decorator BDD Tests: Added extensive BDD test suite for cache decorators    |
| [4.0.0](4.0.0.md)   | 2025-12-08 | Error System Migration to T-Strings: Refactored error system to use t-string template format... |
