"""HashiCorp Vault configuration."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class VaultAppRoleConfig(BaseModel):
    """AppRole auth settings."""

    model_config = ConfigDict(extra="forbid")

    ROLE_ID: str | None = Field(default=None, description="AppRole role_id")
    SECRET_ID: SecretStr | None = Field(default=None, description="AppRole secret_id")
    SECRET_ID_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the AppRole secret_id; takes precedence over APPROLE_SECRET_ID",
    )
    MOUNT_POINT: str = Field(default="approle", description="Mount point of the AppRole auth method")


class VaultKubernetesConfig(BaseModel):
    """Kubernetes auth settings."""

    model_config = ConfigDict(extra="forbid")

    ROLE: str | None = Field(
        default=None,
        description="Vault role bound to the Kubernetes service account",
    )
    JWT_PATH: str = Field(
        default="/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Path to the service account JWT used for Kubernetes auth",
    )
    MOUNT_POINT: str = Field(
        default="kubernetes",
        description="Mount point of the Kubernetes auth method",
    )


class VaultUserpassConfig(BaseModel):
    """Userpass auth mount."""

    model_config = ConfigDict(extra="forbid")

    MOUNT_POINT: str = Field(default="userpass", description="Mount point of the userpass auth method")


class VaultLdapConfig(BaseModel):
    """LDAP auth mount."""

    model_config = ConfigDict(extra="forbid")

    MOUNT_POINT: str = Field(default="ldap", description="Mount point of the LDAP auth method")


class VaultOktaConfig(BaseModel):
    """Okta auth mount."""

    model_config = ConfigDict(extra="forbid")

    MOUNT_POINT: str = Field(default="okta", description="Mount point of the Okta auth method")


class VaultJwtConfig(BaseModel):
    """JWT auth settings."""

    model_config = ConfigDict(extra="forbid")

    ROLE: str | None = Field(default=None, description="Role name for JWT auth")
    JWT: SecretStr | None = Field(default=None, description="JWT for JWT auth")
    JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the JWT; takes precedence over JWT",
    )
    MOUNT_POINT: str = Field(default="jwt", description="Mount path of the JWT auth method")


class VaultAwsConfig(BaseModel):
    """AWS IAM auth settings."""

    model_config = ConfigDict(extra="forbid")

    ACCESS_KEY: str | None = Field(default=None, description="AWS access key for IAM auth")
    SECRET_KEY: SecretStr | None = Field(default=None, description="AWS secret key for IAM auth")
    SESSION_TOKEN: SecretStr | None = Field(
        default=None,
        description="Optional AWS session token for IAM auth",
    )
    ROLE: str | None = Field(default=None, description="Optional Vault role for AWS IAM auth")
    REGION: str = Field(default="us-east-1", description="AWS region used for IAM auth signing")
    MOUNT_POINT: str = Field(default="aws", description="Mount point of the AWS auth method")


class VaultAzureConfig(BaseModel):
    """Azure auth settings."""

    model_config = ConfigDict(extra="forbid")

    ROLE: str | None = Field(default=None, description="Role name for Azure auth")
    JWT: SecretStr | None = Field(default=None, description="JWT for Azure auth")
    JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the Azure JWT; takes precedence over AZURE_JWT",
    )
    SUBSCRIPTION_ID: str | None = Field(default=None, description="Optional Azure subscription id")
    RESOURCE_GROUP_NAME: str | None = Field(default=None, description="Optional Azure resource group name")
    VM_NAME: str | None = Field(default=None, description="Optional Azure VM name")
    VMSS_NAME: str | None = Field(default=None, description="Optional Azure VMSS name")
    MOUNT_POINT: str = Field(default="azure", description="Mount point of the Azure auth method")


class VaultGcpConfig(BaseModel):
    """GCP auth settings."""

    model_config = ConfigDict(extra="forbid")

    ROLE: str | None = Field(default=None, description="Role name for GCP auth")
    JWT: SecretStr | None = Field(default=None, description="JWT for GCP auth")
    JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the GCP JWT; takes precedence over GCP_JWT",
    )
    MOUNT_POINT: str = Field(default="gcp", description="Mount point of the GCP auth method")


class VaultGithubConfig(BaseModel):
    """GitHub auth settings."""

    model_config = ConfigDict(extra="forbid")

    TOKEN: SecretStr | None = Field(
        default=None,
        description="GitHub personal access token for GitHub auth",
    )
    TOKEN_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the GitHub token; takes precedence over GITHUB_TOKEN",
    )
    MOUNT_POINT: str = Field(default="github", description="Mount point of the GitHub auth method")


class VaultCertConfig(BaseModel):
    """TLS client certificate auth settings."""

    model_config = ConfigDict(extra="forbid")

    NAME: str = Field(
        default="",
        description="Optional named cert role for the cert auth method",
    )
    MOUNT_POINT: str = Field(default="cert", description="Mount point of the cert auth method")


class VaultTlsConfig(BaseModel):
    """TLS and mutual TLS settings."""

    model_config = ConfigDict(extra="forbid")

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


class VaultHttpConfig(BaseModel):
    """Request timeouts and retries."""

    model_config = ConfigDict(extra="forbid")

    CONNECT_TIMEOUT: float = Field(default=5.0, description="Connection timeout in seconds")
    READ_TIMEOUT: float = Field(default=10.0, description="Read timeout in seconds")
    RETRIES_MAX_ATTEMPTS: int = Field(default=3, description="Maximum retry attempts for failed requests")


class VaultTokenRenewalConfig(BaseModel):
    """Token renewal settings (adapter only)."""

    model_config = ConfigDict(extra="forbid")

    AUTO_RENEW_TOKEN: bool = Field(
        default=False,
        description="Automatically renew the token before it expires",
    )
    RENEW_THRESHOLD_SECONDS: int = Field(
        default=60,
        description="Renew the token once its remaining TTL drops below this many seconds",
    )


class VaultConfig(BaseModel):
    """Configuration settings for HashiCorp Vault integration.

    Controls connection, authentication, TLS, and secret-retrieval parameters
    for both the BaseConfig settings source and VaultAdapter.

    Auth, TLS, request and token-renewal settings are grouped, for example under ``APPROLE`` and ``TLS``.
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

    TOKEN: SecretStr | None = Field(default=None, description="Vault token (token auth)")
    TOKEN_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the Vault token; takes precedence over TOKEN",
    )
    USERNAME: str | None = Field(default=None, description="Username for userpass/ldap/okta auth")
    PASSWORD: SecretStr | None = Field(default=None, description="Password for userpass/ldap/okta auth")
    PASSWORD_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the password; takes precedence over PASSWORD",
    )
    MOUNT_POINT: str = Field(default="secret", description="Mount point of the KV v2 secrets engine")
    SECRET_PATHS: list[str] = Field(
        default=[],
        description="KV v2 paths read by the settings source; later paths win",
    )
    SECRET_CACHE_TTL: int = Field(
        default=0,
        description="Cache VaultAdapter.read_secret() results for this many seconds; 0 disables caching",
    )

    APPROLE: VaultAppRoleConfig = Field(default_factory=VaultAppRoleConfig, description="AppRole auth settings")
    KUBERNETES: VaultKubernetesConfig = Field(
        default_factory=VaultKubernetesConfig,
        description="Kubernetes auth settings",
    )
    USERPASS: VaultUserpassConfig = Field(default_factory=VaultUserpassConfig, description="Userpass auth mount")
    LDAP: VaultLdapConfig = Field(default_factory=VaultLdapConfig, description="LDAP auth mount")
    OKTA: VaultOktaConfig = Field(default_factory=VaultOktaConfig, description="Okta auth mount")
    JWT_AUTH: VaultJwtConfig = Field(default_factory=VaultJwtConfig, description="JWT auth settings")
    AWS: VaultAwsConfig = Field(default_factory=VaultAwsConfig, description="AWS IAM auth settings")
    AZURE: VaultAzureConfig = Field(default_factory=VaultAzureConfig, description="Azure auth settings")
    GCP: VaultGcpConfig = Field(default_factory=VaultGcpConfig, description="GCP auth settings")
    GITHUB: VaultGithubConfig = Field(default_factory=VaultGithubConfig, description="GitHub auth settings")
    CERT: VaultCertConfig = Field(default_factory=VaultCertConfig, description="TLS client certificate auth settings")
    TLS: VaultTlsConfig = Field(default_factory=VaultTlsConfig, description="TLS and mutual TLS settings")
    HTTP: VaultHttpConfig = Field(default_factory=VaultHttpConfig, description="Request timeouts and retries")
    TOKEN_RENEWAL: VaultTokenRenewalConfig = Field(
        default_factory=VaultTokenRenewalConfig,
        description="Token renewal settings (adapter only)",
    )
