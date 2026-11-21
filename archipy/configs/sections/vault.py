"""HashiCorp Vault configuration."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields


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

    Auth, TLS, request and token-renewal settings are grouped (for example ``APPROLE``, ``TLS``). The flat names
    they replaced (for example ``APPROLE_ROLE_ID``) still work and are deprecated; a value set on a group wins.
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

    APPROLE_ROLE_ID: str | None = Field(
        default=None,
        description="AppRole role_id",
        deprecated=deprecated_flat_message("VAULT", "APPROLE_ROLE_ID", "APPROLE", "ROLE_ID"),
    )
    APPROLE_SECRET_ID: SecretStr | None = Field(
        default=None,
        description="AppRole secret_id",
        deprecated=deprecated_flat_message("VAULT", "APPROLE_SECRET_ID", "APPROLE", "SECRET_ID"),
    )
    APPROLE_SECRET_ID_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the AppRole secret_id; takes precedence over APPROLE_SECRET_ID",
        deprecated=deprecated_flat_message("VAULT", "APPROLE_SECRET_ID_FILE", "APPROLE", "SECRET_ID_FILE"),
    )
    APPROLE_MOUNT_POINT: str = Field(
        default="approle",
        description="Mount point of the AppRole auth method",
        deprecated=deprecated_flat_message("VAULT", "APPROLE_MOUNT_POINT", "APPROLE", "MOUNT_POINT"),
    )
    KUBERNETES_ROLE: str | None = Field(
        default=None,
        description="Vault role bound to the Kubernetes service account",
        deprecated=deprecated_flat_message("VAULT", "KUBERNETES_ROLE", "KUBERNETES", "ROLE"),
    )
    KUBERNETES_JWT_PATH: str = Field(
        default="/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Path to the service account JWT used for Kubernetes auth",
        deprecated=deprecated_flat_message("VAULT", "KUBERNETES_JWT_PATH", "KUBERNETES", "JWT_PATH"),
    )
    KUBERNETES_MOUNT_POINT: str = Field(
        default="kubernetes",
        description="Mount point of the Kubernetes auth method",
        deprecated=deprecated_flat_message("VAULT", "KUBERNETES_MOUNT_POINT", "KUBERNETES", "MOUNT_POINT"),
    )
    USERPASS_MOUNT_POINT: str = Field(
        default="userpass",
        description="Mount point of the userpass auth method",
        deprecated=deprecated_flat_message("VAULT", "USERPASS_MOUNT_POINT", "USERPASS", "MOUNT_POINT"),
    )
    LDAP_MOUNT_POINT: str = Field(
        default="ldap",
        description="Mount point of the LDAP auth method",
        deprecated=deprecated_flat_message("VAULT", "LDAP_MOUNT_POINT", "LDAP", "MOUNT_POINT"),
    )
    OKTA_MOUNT_POINT: str = Field(
        default="okta",
        description="Mount point of the Okta auth method",
        deprecated=deprecated_flat_message("VAULT", "OKTA_MOUNT_POINT", "OKTA", "MOUNT_POINT"),
    )
    JWT_ROLE: str | None = Field(
        default=None,
        description="Role name for JWT auth",
        deprecated=deprecated_flat_message("VAULT", "JWT_ROLE", "JWT_AUTH", "ROLE"),
    )
    JWT: SecretStr | None = Field(
        default=None,
        description="JWT for JWT auth",
        deprecated=deprecated_flat_message("VAULT", "JWT", "JWT_AUTH", "JWT"),
    )
    JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the JWT; takes precedence over JWT",
        deprecated=deprecated_flat_message("VAULT", "JWT_FILE", "JWT_AUTH", "JWT_FILE"),
    )
    JWT_MOUNT_POINT: str = Field(
        default="jwt",
        description="Mount path of the JWT auth method",
        deprecated=deprecated_flat_message("VAULT", "JWT_MOUNT_POINT", "JWT_AUTH", "MOUNT_POINT"),
    )
    AWS_ACCESS_KEY: str | None = Field(
        default=None,
        description="AWS access key for IAM auth",
        deprecated=deprecated_flat_message("VAULT", "AWS_ACCESS_KEY", "AWS", "ACCESS_KEY"),
    )
    AWS_SECRET_KEY: SecretStr | None = Field(
        default=None,
        description="AWS secret key for IAM auth",
        deprecated=deprecated_flat_message("VAULT", "AWS_SECRET_KEY", "AWS", "SECRET_KEY"),
    )
    AWS_SESSION_TOKEN: SecretStr | None = Field(
        default=None,
        description="Optional AWS session token for IAM auth",
        deprecated=deprecated_flat_message("VAULT", "AWS_SESSION_TOKEN", "AWS", "SESSION_TOKEN"),
    )
    AWS_ROLE: str | None = Field(
        default=None,
        description="Optional Vault role for AWS IAM auth",
        deprecated=deprecated_flat_message("VAULT", "AWS_ROLE", "AWS", "ROLE"),
    )
    AWS_REGION: str = Field(
        default="us-east-1",
        description="AWS region used for IAM auth signing",
        deprecated=deprecated_flat_message("VAULT", "AWS_REGION", "AWS", "REGION"),
    )
    AWS_MOUNT_POINT: str = Field(
        default="aws",
        description="Mount point of the AWS auth method",
        deprecated=deprecated_flat_message("VAULT", "AWS_MOUNT_POINT", "AWS", "MOUNT_POINT"),
    )
    AZURE_ROLE: str | None = Field(
        default=None,
        description="Role name for Azure auth",
        deprecated=deprecated_flat_message("VAULT", "AZURE_ROLE", "AZURE", "ROLE"),
    )
    AZURE_JWT: SecretStr | None = Field(
        default=None,
        description="JWT for Azure auth",
        deprecated=deprecated_flat_message("VAULT", "AZURE_JWT", "AZURE", "JWT"),
    )
    AZURE_JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the Azure JWT; takes precedence over AZURE_JWT",
        deprecated=deprecated_flat_message("VAULT", "AZURE_JWT_FILE", "AZURE", "JWT_FILE"),
    )
    AZURE_SUBSCRIPTION_ID: str | None = Field(
        default=None,
        description="Optional Azure subscription id",
        deprecated=deprecated_flat_message("VAULT", "AZURE_SUBSCRIPTION_ID", "AZURE", "SUBSCRIPTION_ID"),
    )
    AZURE_RESOURCE_GROUP_NAME: str | None = Field(
        default=None,
        description="Optional Azure resource group name",
        deprecated=deprecated_flat_message("VAULT", "AZURE_RESOURCE_GROUP_NAME", "AZURE", "RESOURCE_GROUP_NAME"),
    )
    AZURE_VM_NAME: str | None = Field(
        default=None,
        description="Optional Azure VM name",
        deprecated=deprecated_flat_message("VAULT", "AZURE_VM_NAME", "AZURE", "VM_NAME"),
    )
    AZURE_VMSS_NAME: str | None = Field(
        default=None,
        description="Optional Azure VMSS name",
        deprecated=deprecated_flat_message("VAULT", "AZURE_VMSS_NAME", "AZURE", "VMSS_NAME"),
    )
    AZURE_MOUNT_POINT: str = Field(
        default="azure",
        description="Mount point of the Azure auth method",
        deprecated=deprecated_flat_message("VAULT", "AZURE_MOUNT_POINT", "AZURE", "MOUNT_POINT"),
    )
    GCP_ROLE: str | None = Field(
        default=None,
        description="Role name for GCP auth",
        deprecated=deprecated_flat_message("VAULT", "GCP_ROLE", "GCP", "ROLE"),
    )
    GCP_JWT: SecretStr | None = Field(
        default=None,
        description="JWT for GCP auth",
        deprecated=deprecated_flat_message("VAULT", "GCP_JWT", "GCP", "JWT"),
    )
    GCP_JWT_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the GCP JWT; takes precedence over GCP_JWT",
        deprecated=deprecated_flat_message("VAULT", "GCP_JWT_FILE", "GCP", "JWT_FILE"),
    )
    GCP_MOUNT_POINT: str = Field(
        default="gcp",
        description="Mount point of the GCP auth method",
        deprecated=deprecated_flat_message("VAULT", "GCP_MOUNT_POINT", "GCP", "MOUNT_POINT"),
    )
    GITHUB_TOKEN: SecretStr | None = Field(
        default=None,
        description="GitHub personal access token for GitHub auth",
        deprecated=deprecated_flat_message("VAULT", "GITHUB_TOKEN", "GITHUB", "TOKEN"),
    )
    GITHUB_TOKEN_FILE: str | None = Field(
        default=None,
        description="Path to a file containing the GitHub token; takes precedence over GITHUB_TOKEN",
        deprecated=deprecated_flat_message("VAULT", "GITHUB_TOKEN_FILE", "GITHUB", "TOKEN_FILE"),
    )
    GITHUB_MOUNT_POINT: str = Field(
        default="github",
        description="Mount point of the GitHub auth method",
        deprecated=deprecated_flat_message("VAULT", "GITHUB_MOUNT_POINT", "GITHUB", "MOUNT_POINT"),
    )
    CERT_NAME: str = Field(
        default="",
        description="Optional named cert role for the cert auth method",
        deprecated=deprecated_flat_message("VAULT", "CERT_NAME", "CERT", "NAME"),
    )
    CERT_MOUNT_POINT: str = Field(
        default="cert",
        description="Mount point of the cert auth method",
        deprecated=deprecated_flat_message("VAULT", "CERT_MOUNT_POINT", "CERT", "MOUNT_POINT"),
    )
    VERIFY_SSL: bool = Field(
        default=True,
        description="Verify the Vault server's TLS certificate",
        deprecated=deprecated_flat_message("VAULT", "VERIFY_SSL", "TLS", "VERIFY_SSL"),
    )
    CA_CERT_PATH: str | None = Field(
        default=None,
        description="Path to a CA bundle for verifying Vault's TLS certificate",
        deprecated=deprecated_flat_message("VAULT", "CA_CERT_PATH", "TLS", "CA_CERT_PATH"),
    )
    CLIENT_CERT_PATH: str | None = Field(
        default=None,
        description="Path to a client certificate for mutual TLS",
        deprecated=deprecated_flat_message("VAULT", "CLIENT_CERT_PATH", "TLS", "CLIENT_CERT_PATH"),
    )
    CLIENT_KEY_PATH: str | None = Field(
        default=None,
        description="Path to the client private key for mutual TLS",
        deprecated=deprecated_flat_message("VAULT", "CLIENT_KEY_PATH", "TLS", "CLIENT_KEY_PATH"),
    )
    CONNECT_TIMEOUT: float = Field(
        default=5.0,
        description="Connection timeout in seconds",
        deprecated=deprecated_flat_message("VAULT", "CONNECT_TIMEOUT", "HTTP", "CONNECT_TIMEOUT"),
    )
    READ_TIMEOUT: float = Field(
        default=10.0,
        description="Read timeout in seconds",
        deprecated=deprecated_flat_message("VAULT", "READ_TIMEOUT", "HTTP", "READ_TIMEOUT"),
    )
    RETRIES_MAX_ATTEMPTS: int = Field(
        default=3,
        description="Maximum retry attempts for failed requests",
        deprecated=deprecated_flat_message("VAULT", "RETRIES_MAX_ATTEMPTS", "HTTP", "RETRIES_MAX_ATTEMPTS"),
    )
    AUTO_RENEW_TOKEN: bool = Field(
        default=False,
        description="Automatically renew the token before it expires",
        deprecated=deprecated_flat_message("VAULT", "AUTO_RENEW_TOKEN", "TOKEN_RENEWAL", "AUTO_RENEW_TOKEN"),
    )
    RENEW_THRESHOLD_SECONDS: int = Field(
        default=60,
        description="Renew the token once its remaining TTL drops below this many seconds",
        deprecated=deprecated_flat_message(
            "VAULT",
            "RENEW_THRESHOLD_SECONDS",
            "TOKEN_RENEWAL",
            "RENEW_THRESHOLD_SECONDS",
        ),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "APPROLE",
            VaultAppRoleConfig,
            {
                "APPROLE_ROLE_ID": "ROLE_ID",
                "APPROLE_SECRET_ID": "SECRET_ID",
                "APPROLE_SECRET_ID_FILE": "SECRET_ID_FILE",
                "APPROLE_MOUNT_POINT": "MOUNT_POINT",
            },
        )
        fold_flat_fields(
            self,
            "KUBERNETES",
            VaultKubernetesConfig,
            {"KUBERNETES_ROLE": "ROLE", "KUBERNETES_JWT_PATH": "JWT_PATH", "KUBERNETES_MOUNT_POINT": "MOUNT_POINT"},
        )
        fold_flat_fields(self, "USERPASS", VaultUserpassConfig, {"USERPASS_MOUNT_POINT": "MOUNT_POINT"})
        fold_flat_fields(self, "LDAP", VaultLdapConfig, {"LDAP_MOUNT_POINT": "MOUNT_POINT"})
        fold_flat_fields(self, "OKTA", VaultOktaConfig, {"OKTA_MOUNT_POINT": "MOUNT_POINT"})
        fold_flat_fields(
            self,
            "JWT_AUTH",
            VaultJwtConfig,
            {"JWT_ROLE": "ROLE", "JWT": "JWT", "JWT_FILE": "JWT_FILE", "JWT_MOUNT_POINT": "MOUNT_POINT"},
        )
        fold_flat_fields(
            self,
            "AWS",
            VaultAwsConfig,
            {
                "AWS_ACCESS_KEY": "ACCESS_KEY",
                "AWS_SECRET_KEY": "SECRET_KEY",
                "AWS_SESSION_TOKEN": "SESSION_TOKEN",
                "AWS_ROLE": "ROLE",
                "AWS_REGION": "REGION",
                "AWS_MOUNT_POINT": "MOUNT_POINT",
            },
        )
        fold_flat_fields(
            self,
            "AZURE",
            VaultAzureConfig,
            {
                "AZURE_ROLE": "ROLE",
                "AZURE_JWT": "JWT",
                "AZURE_JWT_FILE": "JWT_FILE",
                "AZURE_SUBSCRIPTION_ID": "SUBSCRIPTION_ID",
                "AZURE_RESOURCE_GROUP_NAME": "RESOURCE_GROUP_NAME",
                "AZURE_VM_NAME": "VM_NAME",
                "AZURE_VMSS_NAME": "VMSS_NAME",
                "AZURE_MOUNT_POINT": "MOUNT_POINT",
            },
        )
        fold_flat_fields(
            self,
            "GCP",
            VaultGcpConfig,
            {"GCP_ROLE": "ROLE", "GCP_JWT": "JWT", "GCP_JWT_FILE": "JWT_FILE", "GCP_MOUNT_POINT": "MOUNT_POINT"},
        )
        fold_flat_fields(
            self,
            "GITHUB",
            VaultGithubConfig,
            {"GITHUB_TOKEN": "TOKEN", "GITHUB_TOKEN_FILE": "TOKEN_FILE", "GITHUB_MOUNT_POINT": "MOUNT_POINT"},
        )
        fold_flat_fields(self, "CERT", VaultCertConfig, {"CERT_NAME": "NAME", "CERT_MOUNT_POINT": "MOUNT_POINT"})
        fold_flat_fields(
            self,
            "TLS",
            VaultTlsConfig,
            {
                "VERIFY_SSL": "VERIFY_SSL",
                "CA_CERT_PATH": "CA_CERT_PATH",
                "CLIENT_CERT_PATH": "CLIENT_CERT_PATH",
                "CLIENT_KEY_PATH": "CLIENT_KEY_PATH",
            },
        )
        fold_flat_fields(
            self,
            "HTTP",
            VaultHttpConfig,
            {
                "CONNECT_TIMEOUT": "CONNECT_TIMEOUT",
                "READ_TIMEOUT": "READ_TIMEOUT",
                "RETRIES_MAX_ATTEMPTS": "RETRIES_MAX_ATTEMPTS",
            },
        )
        fold_flat_fields(
            self,
            "TOKEN_RENEWAL",
            VaultTokenRenewalConfig,
            {"AUTO_RENEW_TOKEN": "AUTO_RENEW_TOKEN", "RENEW_THRESHOLD_SECONDS": "RENEW_THRESHOLD_SECONDS"},
        )
        return self
