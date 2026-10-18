"""HashiCorp Vault configuration."""

from typing import Literal

from pydantic import BaseModel, Field


class VaultConfig(BaseModel):
    """Configuration settings for HashiCorp Vault integration.

    Controls connection, authentication, TLS, and secret-retrieval parameters
    for both the BaseConfig settings source and VaultAdapter.
    """

    ENABLED: bool = Field(default=False, description="Whether Vault integration is active")
    ADDR: str | None = Field(default=None, description="Vault server address, e.g. https://vault.example.com:8200")
    NAMESPACE: str | None = Field(default=None, description="Vault Enterprise namespace")
    AUTH_METHOD: Literal[
        "token",
        "approle",
        "kubernetes",
        "userpass",
        "ldap",
        "okta",
        "jwt",
        "aws",
        "azure",
        "gcp",
        "github",
        "cert",
    ] = Field(
        default="token",
        description="Vault auth method (hvac-supported backends)",
    )

    # Token auth
    TOKEN: str | None = Field(default=None, description="Vault token (token auth)")
    TOKEN_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the Vault token; takes precedence over TOKEN",
    )

    # AppRole auth
    APPROLE_ROLE_ID: str | None = Field(default=None, description="AppRole role_id")
    APPROLE_SECRET_ID: str | None = Field(default=None, description="AppRole secret_id")
    APPROLE_SECRET_ID_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the AppRole secret_id; takes precedence over APPROLE_SECRET_ID",
    )
    APPROLE_MOUNT_POINT: str = Field(default="approle", description="Mount point of the AppRole auth method")

    # Kubernetes auth
    KUBERNETES_ROLE: str | None = Field(
        default=None,
        description="Vault role bound to the Kubernetes service account",
    )
    KUBERNETES_JWT_PATH: str = Field(
        default="/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Path to the service account JWT used for Kubernetes auth",
    )
    KUBERNETES_MOUNT_POINT: str = Field(
        default="kubernetes",
        description="Mount point of the Kubernetes auth method",
    )

    # Username/password auth (userpass, ldap, okta)
    USERNAME: str | None = Field(default=None, description="Username for userpass/ldap/okta auth")
    PASSWORD: str | None = Field(default=None, description="Password for userpass/ldap/okta auth")
    PASSWORD_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the password; takes precedence over PASSWORD",
    )
    USERPASS_MOUNT_POINT: str = Field(default="userpass", description="Mount point of the userpass auth method")
    LDAP_MOUNT_POINT: str = Field(default="ldap", description="Mount point of the LDAP auth method")
    OKTA_MOUNT_POINT: str = Field(default="okta", description="Mount point of the Okta auth method")

    # JWT auth
    JWT_ROLE: str | None = Field(default=None, description="Role name for JWT auth")
    JWT: str | None = Field(default=None, description="JWT for JWT auth")
    JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the JWT; takes precedence over JWT",
    )
    JWT_MOUNT_POINT: str = Field(default="jwt", description="Mount path of the JWT auth method")

    # AWS IAM auth
    AWS_ACCESS_KEY: str | None = Field(default=None, description="AWS access key for IAM auth")
    AWS_SECRET_KEY: str | None = Field(default=None, description="AWS secret key for IAM auth")
    AWS_SESSION_TOKEN: str | None = Field(default=None, description="Optional AWS session token for IAM auth")
    AWS_ROLE: str | None = Field(default=None, description="Optional Vault role for AWS IAM auth")
    AWS_REGION: str = Field(default="us-east-1", description="AWS region used for IAM auth signing")
    AWS_MOUNT_POINT: str = Field(default="aws", description="Mount point of the AWS auth method")

    # Azure auth
    AZURE_ROLE: str | None = Field(default=None, description="Role name for Azure auth")
    AZURE_JWT: str | None = Field(default=None, description="JWT for Azure auth")
    AZURE_JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the Azure JWT; takes precedence over AZURE_JWT",
    )
    AZURE_SUBSCRIPTION_ID: str | None = Field(default=None, description="Optional Azure subscription id")
    AZURE_RESOURCE_GROUP_NAME: str | None = Field(default=None, description="Optional Azure resource group name")
    AZURE_VM_NAME: str | None = Field(default=None, description="Optional Azure VM name")
    AZURE_VMSS_NAME: str | None = Field(default=None, description="Optional Azure VMSS name")
    AZURE_MOUNT_POINT: str = Field(default="azure", description="Mount point of the Azure auth method")

    # GCP auth
    GCP_ROLE: str | None = Field(default=None, description="Role name for GCP auth")
    GCP_JWT: str | None = Field(default=None, description="JWT for GCP auth")
    GCP_JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the GCP JWT; takes precedence over GCP_JWT",
    )
    GCP_MOUNT_POINT: str = Field(default="gcp", description="Mount point of the GCP auth method")

    # GitHub auth
    GITHUB_TOKEN: str | None = Field(default=None, description="GitHub personal access token for GitHub auth")
    GITHUB_TOKEN_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the GitHub token; takes precedence over GITHUB_TOKEN",
    )
    GITHUB_MOUNT_POINT: str = Field(default="github", description="Mount point of the GitHub auth method")

    # Cert auth (TLS client certificate auth method; often paired with CLIENT_CERT_PATH/KEY)
    CERT_NAME: str = Field(
        default="",
        description="Optional named cert role for the cert auth method",
    )
    CERT_MOUNT_POINT: str = Field(default="cert", description="Mount point of the cert auth method")

    # KV v2
    MOUNT_POINT: str = Field(default="secret", description="Mount point of the KV v2 secrets engine")
    SECRET_PATHS: list[str] = Field(
        default=[],
        description="KV v2 paths read by the settings source; later paths win",
    )

    # TLS / mTLS
    VERIFY_SSL: bool = Field(default=True, description="Verify the Vault server's TLS certificate")
    CA_CERT_PATH: str | None = Field(
        default=None,
        description="Path to a CA bundle for verifying Vault's TLS certificate",
    )
    CLIENT_CERT_PATH: str | None = Field(
        default=None,
        description="Path to a client certificate for mutual TLS",
    )
    CLIENT_KEY_PATH: str | None = Field(
        default=None,
        description="Path to the client private key for mutual TLS",
    )

    # Timeouts / retries
    CONNECT_TIMEOUT: float = Field(default=5.0, description="Connection timeout in seconds")
    READ_TIMEOUT: float = Field(default=10.0, description="Read timeout in seconds")
    RETRIES_MAX_ATTEMPTS: int = Field(default=3, description="Maximum retry attempts for failed requests")

    # Token lifecycle (adapter only — the settings source is one-shot at startup)
    AUTO_RENEW_TOKEN: bool = Field(
        default=False,
        description="Automatically renew the token before it expires",
    )
    RENEW_THRESHOLD_SECONDS: int = Field(
        default=60,
        description="Renew the token once its remaining TTL drops below this many seconds",
    )

    # Secret caching (adapter only)
    SECRET_CACHE_TTL: int = Field(
        default=0,
        description="Cache VaultAdapter.read_secret() results for this many seconds; 0 disables caching",
    )
