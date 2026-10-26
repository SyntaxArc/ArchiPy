import time
import uuid

from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts
from features.test_helpers import realm_issuer
from jwcrypto import jwk, jwt

from archipy.models.dtos.keycloak.client_dtos import KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import KeycloakIdentityProviderRequestDTO
from archipy.models.dtos.keycloak.token_exchange_dtos import KeycloakTokenExchangeRequestDTO, KeycloakTokenExchangeResponseDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakFederatedIdentityRequestDTO
from archipy.models.types import TokenExchangeTokenType


EXTERNAL_ISSUER = "https://external-idp.example.com"


@when('I enable standard token exchange on the client "{client}" using {adapter_type} adapter')
async def step_enable_token_exchange(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    uuid_ = await _adapter_call(adapter, is_async, "get_client_id", client)
    current = await _adapter_call(adapter, is_async, "get_client", uuid_)
    attributes = {**(current.attributes or {}), "standard.token.exchange.enabled": "true"}
    await _adapter_call(adapter, is_async, "update_client", uuid_, KeycloakClientRequestDTO(client_id=client, attributes=attributes))


@then('the access token of "{username}" with password "{password}" is exchanged for another access token and an ID token using {adapter_type} adapter')
async def step_token_exchange(context: Context, username: str, password: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    token = await _adapter_call(adapter, is_async, "get_token", username, password)
    exchanged = await _adapter_call(
        adapter, is_async, "token_exchange", KeycloakTokenExchangeRequestDTO(subject_token=token.access_token),
    )
    assert isinstance(exchanged, KeycloakTokenExchangeResponseDTO), exchanged
    assert exchanged.access_token and exchanged.access_token != token.access_token, exchanged
    assert exchanged.issued_token_type == TokenExchangeTokenType.ACCESS_TOKEN, exchanged
    id_exchange = await _adapter_call(
        adapter, is_async, "token_exchange",
        KeycloakTokenExchangeRequestDTO(
            subject_token=token.access_token,
            requested_token_type=TokenExchangeTokenType.ID_TOKEN,
            audience=[adapter.configs.CLIENT_ID],
        ),
    )
    assert id_exchange.issued_token_type == TokenExchangeTokenType.ID_TOKEN, id_exchange
    assert id_exchange.access_token, id_exchange


@when('I trust an external issuer for the client "{client}" and link user "{username}" as "{external}" using {adapter_type} adapter')
async def step_trust_external_issuer(context: Context, client: str, username: str, external: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    key = jwk.JWK.generate(kty="RSA", size=2048, kid="external-key")
    sc.store("external_key", key)
    alias = f"jwt-idp-{uuid.uuid4().hex[:6]}"
    issuer = f"{EXTERNAL_ISSUER}/{alias}"
    sc.store("external_issuer", issuer)
    public_pem = "".join(
        line for line in key.export_to_pem(private_key=False, password=None).decode().splitlines() if "-----" not in line
    )
    provider = KeycloakIdentityProviderRequestDTO(
        alias=alias,
        provider_id="oidc",
        enabled=True,
        config={
            "issuer": issuer,
            "clientId": "external",
            "clientSecret": "secret",
            "authorizationUrl": f"{issuer}/auth",
            "tokenUrl": f"{issuer}/token",
            "validateSignature": "true",
            "useJwksUrl": "false",
            "publicKeySignatureVerifier": public_pem,
            "publicKeySignatureVerifierKeyId": "external-key",
            "jwtAuthorizationGrantEnabled": "true",
            "jwtAuthorizationGrantAssertionSignatureAlg": "RS256",
        },
    )
    await _adapter_call(adapter, is_async, "create_identity_provider", provider)
    sc.store("external_idp_alias", alias)
    client_uuid = await _adapter_call(adapter, is_async, "get_client_id", client)
    current = await _adapter_call(adapter, is_async, "get_client", client_uuid)
    attributes = {
        **(current.attributes or {}),
        "oauth2.jwt.authorization.grant.enabled": "true",
        "oauth2.jwt.authorization.grant.idp": alias,
    }
    await _adapter_call(adapter, is_async, "update_client", client_uuid, KeycloakClientRequestDTO(client_id=client, attributes=attributes))
    link = KeycloakFederatedIdentityRequestDTO(identity_provider=alias, user_id=f"ext-{external}", user_name=external)
    await _adapter_call(adapter, is_async, "add_user_federated_identity", sc.get(f"user_id_{username}"), alias, link)
    sc.store("external_subject", f"ext-{external}")


@then("a JWT signed by the external issuer is traded for an access token using {adapter_type} adapter")
async def step_jwt_bearer_grant(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    now = int(time.time())
    realm_issuer_url = realm_issuer(adapter.configs.SERVER_URL, adapter.configs.REALM_NAME)
    claims = {"iss": sc.get("external_issuer"), "sub": sc.get("external_subject"), "aud": realm_issuer_url, "exp": now + 120, "iat": now, "jti": uuid.uuid4().hex}
    assertion = jwt.JWT(header={"alg": "RS256", "kid": "external-key"}, claims=claims)
    assertion.make_signed_token(sc.get("external_key"))
    token = await _adapter_call(adapter, is_async, "jwt_bearer_grant", assertion.serialize(), "openid")
    assert token.access_token and token.refresh_token is None, token
