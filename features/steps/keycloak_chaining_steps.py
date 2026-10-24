from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter, KeycloakAdapter
from archipy.configs.config_template import KeycloakConfig
from archipy.models.dtos.keycloak.client_dtos import KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import KeycloakIdentityProviderRequestDTO
from archipy.models.dtos.keycloak.protocol_mapper_config_dtos import KeycloakOidcAudienceMapperConfigDTO
from archipy.models.dtos.keycloak.token_exchange_dtos import KeycloakTokenExchangeRequestDTO
from archipy.models.dtos.keycloak.user_dtos import (
    KeycloakCredentialRequestDTO,
    KeycloakFederatedIdentityRequestDTO,
    KeycloakUserRequestDTO,
)


def _switch_realm(adapter, realm: str) -> None:
    """Point the admin client of the shared test adapter at ``realm``."""
    adapter.configs.REALM_NAME = realm
    adapter._admin_adapter = None
    adapter._admin_token_expiry = 0
    adapter._initialize_admin_client()


def _issuer(adapter, realm: str) -> str:
    return f"{adapter.configs.SERVER_URL.rstrip('/')}/realms/{realm}"


def _client_adapter(adapter, is_async: bool, realm: str, client: str, secret: str):
    """Build an adapter that talks to ``realm`` as ``client`` (token endpoint only, no admin mode)."""
    configs = KeycloakConfig(
        SERVER_URL=adapter.configs.SERVER_URL,
        REALM_NAME=realm,
        CLIENT_ID=client,
        CLIENT_SECRET_KEY=secret,
        VERIFY_SSL=False,
        IS_ADMIN_MODE_ENABLED=False,
    )
    return AsyncKeycloakAdapter(configs) if is_async else KeycloakAdapter(configs)


async def _confidential_client(adapter, is_async: bool, realm: str, client_id: str, **kwargs) -> tuple[str, str]:
    """Create a confidential client in ``realm`` and return its UUID and secret."""
    await _adapter_call(
        adapter, is_async, "create_client", client_id, realm=realm, skip_exists=True,
        public_client=False, service_account_enabled=False, direct_access_grants_enabled=True, **kwargs,
    )
    uuid = await _adapter_call(adapter, is_async, "get_client_id", client_id)
    secret = (await _adapter_call(adapter, is_async, "get_client_secret_credential", uuid)).value
    return uuid, secret


@when('I set up domain A "{realm_a}" with client "{client_a}", user "{username}" and domain B "{realm_b}" as an audience using {adapter_type} adapter')
async def step_setup_domain_a(
    context: Context, realm_a: str, client_a: str, username: str, realm_b: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    original_realm = adapter.configs.REALM_NAME
    for realm in (realm_a, realm_b):
        await _adapter_call(adapter, is_async, "create_realm", realm, skip_exists=True)
    issuer_b = _issuer(adapter, realm_b)
    _switch_realm(adapter, realm_a)
    # domain B is represented in domain A by a client whose id is B's issuer; its secret is used by B's identity provider
    _, secret_b = await _confidential_client(
        adapter, is_async, realm_a, issuer_b, redirect_uris=[f"/realms/{realm_b}/broker/{realm_a}/endpoint/*"],
    )
    uuid_a, secret_a = await _confidential_client(adapter, is_async, realm_a, client_a, standard_flow_enabled=True)
    current = await _adapter_call(adapter, is_async, "get_client", uuid_a)
    attributes = {**(current.attributes or {}), "standard.token.exchange.enabled": "true"}
    await _adapter_call(adapter, is_async, "update_client", uuid_a, KeycloakClientRequestDTO(client_id=client_a, attributes=attributes))
    scope_id = await _adapter_call(
        adapter, is_async, "create_client_scope",
        KeycloakClientScopeRequestDTO(name="access-domainb", protocol="openid-connect", attributes={"include.in.token.scope": "false"}),
        skip_exists=True,
    )
    await _adapter_call(
        adapter, is_async, "add_client_scope_mapper_with_config", scope_id, "audience-domainb",
        KeycloakOidcAudienceMapperConfigDTO(included_client_audience=issuer_b),
    )
    await _adapter_call(adapter, is_async, "add_client_optional_client_scope", uuid_a, scope_id, KeycloakClientScopeRequestDTO())
    user_id = await _adapter_call(
        adapter, is_async, "create_user",
        KeycloakUserRequestDTO(
            username=username, enabled=True, email_verified=True, first_name="Chain", last_name="User", email=f"{username}@a.test",
            credentials=[KeycloakCredentialRequestDTO(type="password", value="pass123", temporary=False)],
        ),
    )
    keys = await _adapter_call(adapter, is_async, "get_realm_keys")
    rs256 = next(k for k in keys.keys_value if k.algorithm == "RS256" and k.use == "SIG")
    sc.store(
        "chain", {
            "a": realm_a, "b": realm_b, "client_a": client_a, "secret_a": secret_a, "secret_b_client": secret_b,
            "issuer_a": _issuer(adapter, realm_a), "issuer_b": issuer_b, "user_a_id": user_id, "username": username,
            "public_key": rs256.public_key, "kid": rs256.kid,
        },
    )
    adapter.configs.REALM_NAME = original_realm


@when('I set up domain B "{realm_b}" with client "{client_b}" trusting domain A through the identity provider "{alias}" using {adapter_type} adapter')
async def step_setup_domain_b(context: Context, realm_b: str, client_b: str, alias: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    chain = sc.get("chain")
    original_realm = adapter.configs.REALM_NAME
    _switch_realm(adapter, realm_b)
    await _adapter_call(
        adapter, is_async, "create_identity_provider",
        KeycloakIdentityProviderRequestDTO(
            alias=alias, provider_id="oidc", enabled=True,
            config={
                "issuer": chain["issuer_a"],
                "clientId": chain["issuer_b"],
                "clientSecret": chain["secret_b_client"],
                "authorizationUrl": f"{chain['issuer_a']}/protocol/openid-connect/auth",
                "tokenUrl": f"{chain['issuer_a']}/protocol/openid-connect/token",
                "validateSignature": "true",
                "useJwksUrl": "false",
                "publicKeySignatureVerifier": chain["public_key"],
                "publicKeySignatureVerifierKeyId": chain["kid"],
                "jwtAuthorizationGrantEnabled": "true",
                "jwtAuthorizationGrantAssertionSignatureAlg": "RS256",
            },
        ),
    )
    uuid_b, secret_b = await _confidential_client(adapter, is_async, realm_b, client_b)
    current = await _adapter_call(adapter, is_async, "get_client", uuid_b)
    attributes = {
        **(current.attributes or {}),
        "oauth2.jwt.authorization.grant.enabled": "true",
        "oauth2.jwt.authorization.grant.idp": alias,
    }
    await _adapter_call(adapter, is_async, "update_client", uuid_b, KeycloakClientRequestDTO(client_id=client_b, attributes=attributes))
    user_b_id = await _adapter_call(
        adapter, is_async, "create_user",
        KeycloakUserRequestDTO(username=f"{chain['username']}-b", enabled=True, email=f"{chain['username']}@b.test"),
    )
    # domain B knows the user by the subject domain A puts in its tokens: the id of the user in domain A
    await _adapter_call(
        adapter, is_async, "add_user_federated_identity", user_b_id, alias,
        KeycloakFederatedIdentityRequestDTO(identity_provider=alias, user_id=chain["user_a_id"], user_name=chain["username"]),
    )
    sc.store("chain", {**chain, "client_b": client_b, "secret_b": secret_b, "user_b_id": user_b_id})
    adapter.configs.REALM_NAME = original_realm


@then("a token from domain A is exchanged for a JWT assertion and redeemed in domain B using {adapter_type} adapter")
async def step_chain_tokens(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    chain = sc.get("chain")
    adapter_a = _client_adapter(adapter, is_async, chain["a"], chain["client_a"], chain["secret_a"])
    token1 = await _adapter_call(adapter_a, is_async, "get_token", chain["username"], "pass123")
    token2 = await _adapter_call(
        adapter_a, is_async, "token_exchange",
        KeycloakTokenExchangeRequestDTO(subject_token=token1.access_token, audience=chain["issuer_b"], scope="access-domainb"),
    )
    assert token2.access_token and token2.access_token != token1.access_token, token2
    assertion_claims = await _adapter_call(adapter_a, is_async, "get_token_info", token2.access_token)
    audience = assertion_claims.aud if isinstance(assertion_claims.aud, list) else [assertion_claims.aud]
    assert chain["issuer_b"] in audience, assertion_claims
    adapter_b = _client_adapter(adapter, is_async, chain["b"], chain["client_b"], chain["secret_b"])
    token3 = await _adapter_call(adapter_b, is_async, "jwt_bearer_grant", token2.access_token, "profile")
    assert token3.access_token and token3.refresh_token is None, token3
    claims3 = await _adapter_call(adapter_b, is_async, "get_token_info", token3.access_token)
    assert claims3.iss == chain["issuer_b"], claims3
    assert claims3.sub == chain["user_b_id"], (claims3.sub, chain["user_b_id"])
