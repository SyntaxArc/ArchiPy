"""Configuration for test containers used in Behave tests."""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from testcontainers.core.config import testcontainers_config


class TestContainerConfig(BaseSettings):
    """Base configuration for test containers."""

    model_config = SettingsConfigDict(
        env_file=".env.test",
        case_sensitive=True,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Configure testcontainers to use custom ryuk image
        ryuk_image = os.getenv("TESTCONTAINERS_RYUK_CONTAINER_IMAGE")
        if ryuk_image:
            testcontainers_config.ryuk_image = ryuk_image

    # Redis Configuration
    REDIS_IMAGE: str = Field(description="Redis test container image")
    REDIS_PORT: int = Field(description="Redis test container port")
    REDIS_DATABASE: int = Field(description="Redis test container database")
    REDIS_PASSWORD: str | None = Field(description="Redis test container password")

    # PostgreSQL Configuration
    POSTGRES_IMAGE: str = Field(description="PostgreSQL test container image")
    POSTGRES_PORT: int = Field(description="PostgreSQL test container port")
    POSTGRES_DATABASE: str = Field(description="PostgreSQL test container database")
    POSTGRES_USERNAME: str = Field(description="PostgreSQL test container username")
    POSTGRES_PASSWORD: str = Field(description="PostgreSQL test container password")

    # Keycloak Configuration
    KEYCLOAK_IMAGE: str = Field(description="Keycloak test container image")
    KEYCLOAK_PORT: int = Field(description="Keycloak test container port")
    KEYCLOAK_ADMIN_USERNAME: str = Field(description="Keycloak test container admin username")
    KEYCLOAK_ADMIN_PASSWORD: str = Field(description="Keycloak test container admin password")
    KEYCLOAK_REALM: str = Field(description="Keycloak test container realm")

    # Elasticsearch Configuration
    ELASTICSEARCH_IMAGE: str = Field(description="Elasticsearch test container image")
    ELASTICSEARCH_PORT: int = Field(description="Elasticsearch test container port")
    ELASTICSEARCH_USERNAME: str = Field(description="Elasticsearch test container username")
    ELASTICSEARCH_PASSWORD: str = Field(description="Elasticsearch test container password")
    ELASTICSEARCH_CLUSTER_NAME: str = Field(description="Elasticsearch test container cluster name")

    # Kafka Configuration
    KAFKA_IMAGE: str = Field(description="Kafka test container image")
    KAFKA_PORT: int = Field(description="Kafka test container port")

    # MinIO Configuration
    MINIO_IMAGE: str = Field(description="MinIO test container image")
    MINIO_PORT: int = Field(description="MinIO test container port")
    MINIO_ACCESS_KEY: str = Field(description="MinIO test container access key")
    MINIO_SECRET_KEY: str = Field(description="MinIO test container secret key")


# Global instance for easy access
test_config = TestContainerConfig()
