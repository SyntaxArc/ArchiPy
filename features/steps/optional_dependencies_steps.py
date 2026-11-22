"""Step definitions for optional dependency scenarios."""

import os
import subprocess
import sys

from behave import given, then, when
from features.test_helpers import get_current_scenario_context

_BLOCK_JINJA2 = """
import sys
from types import SimpleNamespace

class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name == "jinja2" or name.startswith("jinja2."):
            raise ModuleNotFoundError(f"No module named {name!r}")

sys.meta_path.insert(0, _Blocker())
from archipy.adapters.email.adapters import EmailAdapter

adapter = EmailAdapter.__new__(EmailAdapter)
adapter.config = SimpleNamespace(USERNAME="sender@example.com", FROM_ADDRESS=None)
adapter._create_message("a@example.com", "subject", "plain body")
print("PLAIN_OK")
try:
    adapter._create_message("a@example.com", "subject", "", template="Hello {{ name }}", template_vars={"name": "x"})
except Exception as exception:
    print(type(exception).__name__, exception.additional_data)
"""


@given("jinja2 is not installed")
def step_given_no_jinja2(context):
    get_current_scenario_context(context).store("block_jinja2", True)


@when("I build an email message without and with a template")
def step_when_build_messages(context):
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _BLOCK_JINJA2],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    get_current_scenario_context(context).store("jinja2_result", result)


@then("the plain message should be built")
def step_then_plain_built(context):
    result = get_current_scenario_context(context).get("jinja2_result")
    assert "PLAIN_OK" in result.stdout, f"{result.stdout} {result.stderr[-500:]}"


@then('the template message should fail with a message mentioning "{text}"')
def step_then_template_fails(context, text):
    result = get_current_scenario_context(context).get("jinja2_result")
    assert "ConfigurationError" in result.stdout and text in result.stdout, f"{result.stdout} {result.stderr[-500:]}"


@when('I read the "{extra}" extra of the "{package}" package')
def step_read_package_extra(context, extra, package):
    import tomllib
    from pathlib import Path

    project = tomllib.loads(Path(f"packages/{package}/pyproject.toml").read_text())["project"]
    requirements = project["dependencies"] if extra == "base" else project["optional-dependencies"][extra]
    get_current_scenario_context(context).store("package_requirements", requirements)


@then('it should require "{requirement}"')
def step_requires(context, requirement):
    requirements = get_current_scenario_context(context).get("package_requirements")
    assert any(item.startswith(requirement) for item in requirements), f"{requirement} not in {requirements}"


@then('it should not require "{requirement}"')
def step_does_not_require(context, requirement):
    requirements = get_current_scenario_context(context).get("package_requirements")
    assert not any(item.startswith(requirement) for item in requirements), f"{requirement} found in {requirements}"


@given('a fresh Python process importing "{name}" from "{package}"')
def step_public_import(context, name, package):
    get_current_scenario_context(context).store("public_import", (package, name))


@then('loading "{implementation}" honors the interpreter\'s import timing for "{definition}" and "{dependency}"')
def step_check_import_timing(context, implementation, definition, dependency):
    package, name = get_current_scenario_context(context).get("public_import")
    submodule, canonical_name = definition.rsplit(".", 1)
    module = f"{package}.{submodule}"
    script = f"""
import sys
from importlib import import_module
from {package} import {name}

eager = sys.version_info < (3, 15)
for target in ({module!r}, {dependency!r}):
    assert (target in sys.modules) == eager, (target, eager)

from {package} import {implementation}

assert {module!r} in sys.modules and {dependency!r} in sys.modules
assert {implementation} is getattr(import_module({module!r}), {canonical_name!r})
exports = import_module({package!r}).__all__
assert {name!r} in exports and {implementation!r} in exports
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


@then("importing the base configuration honors the interpreter's import timing")
def step_base_config_import_timing(context):
    script = """
import sys

from archipy.configs.base_config import BaseConfig

eager = sys.version_info < (3, 15)
assert ("archipy.models.errors" in sys.modules) == eager
assert "grpc" not in sys.modules
assert BaseConfig is not None

import archipy.models.errors as errors
_ = errors.ConfigurationError(operation="lazy", reason="config")
assert errors.ConfigurationError.__module__ == "archipy.models.errors.system_errors"
assert "archipy.models.errors.system_errors" in sys.modules
assert "grpc" not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


@then("importing the error package honors the interpreter's import timing")
def step_error_package_import_timing(context):
    script = """
import sys

import archipy.models.errors as errors

eager = sys.version_info < (3, 15)
assert "archipy.models.errors.base_error" in sys.modules
assert ("archipy.models.errors.auth_errors" in sys.modules) == eager
assert ("archipy.models.errors.system_errors" in sys.modules) == eager
assert "grpc" not in sys.modules

error = errors.ConfigurationError(operation="lazy", reason="error")
assert error.code == "CONFIGURATION_ERROR"
assert error.__class__.__module__ == "archipy.models.errors.system_errors"
assert "archipy.models.errors.system_errors" in sys.modules
assert "grpc" not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


@then("the error package works when gRPC is not installed")
def step_error_package_without_grpc(context):
    script = """
import importlib
import pkgutil
import sys

class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name == "grpc" or name.startswith("grpc."):
            raise ModuleNotFoundError(f"No module named {name!r}")
        return None

sys.meta_path.insert(0, Blocker())

import archipy.models.errors as errors
from archipy.models.errors.base_error import BaseError

for module in pkgutil.iter_modules(errors.__path__):
    if module.name != "__init__":
        importlib.import_module(f"{errors.__name__}.{module.name}")

def subclasses(cls):
    found = set()
    for child in cls.__subclasses__():
        if child not in found:
            found.add(child)
            found.update(subclasses(child))
    return found

classes = subclasses(BaseError)
assert len(classes) >= 80, len(classes)
assert all(isinstance(cls.grpc_status, int) and 0 <= cls.grpc_status <= 16 for cls in classes)
assert errors.ConfigurationError(operation="lazy", reason="error").grpc_status == 13
assert "grpc" not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


@then("importing core helpers honors the interpreter's import timing")
def step_core_helper_import_timing(context):
    script = """
import sys

from archipy.adapters.email.adapters import EmailAdapter
from archipy.helpers.errors import capture_exception
from archipy.helpers.utils.app_utils import FastAPIUtils
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.helpers.utils.file_utils import FileUtils
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.helpers.utils.password_utils import PasswordUtils
from archipy.helpers.utils.totp_utils import TOTPUtils

eager = sys.version_info < (3, 15)
assert ("archipy.configs.base_config" in sys.modules) == eager
assert ("archipy.models.errors" in sys.modules) == eager

try:
    PasswordUtils.hash_password("secret")
except AssertionError as error:
    assert "set global configs" in str(error)
else:
    raise AssertionError("Expected hash_password to require global settings")
assert "archipy.configs.base_config" in sys.modules

import archipy.models.errors as errors
_ = errors.InvalidPasswordError()
assert errors.InvalidPasswordError.__module__ == "archipy.models.errors.validation_errors"
assert "archipy.models.errors.validation_errors" in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


@then("importing the public Keycloak ports honors the interpreter's import timing")
def step_keycloak_port_import_timing(context):
    script = """
import sys

from archipy.adapters.keycloak.ports import AsyncKeycloakPort, KeycloakPort

eager = sys.version_info < (3, 15)
mixin_module = "archipy.adapters.keycloak._resources.groups.adapter"
assert ("keycloak" in sys.modules) == eager
assert (mixin_module in sys.modules) == eager

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter, KeycloakAdapter
from archipy.adapters.keycloak._resources import KeycloakGroupsMixin
from archipy.adapters.keycloak._resources.groups.adapter import KeycloakGroupsMixin as CanonicalMixin

assert "keycloak" in sys.modules
assert KeycloakGroupsMixin is CanonicalMixin
assert issubclass(KeycloakAdapter, KeycloakPort)
assert issubclass(KeycloakAdapter, KeycloakGroupsMixin)
assert issubclass(AsyncKeycloakAdapter, AsyncKeycloakPort)
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


@then('the "{package}" adapter can defer global configuration when given explicit settings')
def step_explicit_adapter_config(context, package):
    setup, default_constructor = {
        "redis": (
            """
from archipy.adapters.redis.adapters import RedisAdapter
from archipy.configs.config_template import RedisConfig
adapter = RedisAdapter(RedisConfig())
adapter.close()
""",
            "RedisAdapter()",
        ),
        "elasticsearch": (
            """
from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.configs.config_template import ElasticsearchConfig
adapter = ElasticsearchAdapter(ElasticsearchConfig())
adapter.close()
""",
            "ElasticsearchAdapter()",
        ),
        "kafka": (
            """
from archipy.adapters.kafka.adapters import KafkaProducerAdapter
from archipy.configs.config_template import KafkaConfig
adapter = KafkaProducerAdapter("example", KafkaConfig())
adapter.close()
""",
            'KafkaProducerAdapter("example")',
        ),
        "mysql": (
            """
from archipy.adapters.mysql.sqlalchemy.adapters import MySQLSQLAlchemyAdapter
from archipy.configs.config_template import MySQLSQLAlchemyConfig
adapter = MySQLSQLAlchemyAdapter(MySQLSQLAlchemyConfig())
adapter.session_manager.engine.dispose()
""",
            "MySQLSQLAlchemyAdapter()",
        ),
        "postgres": (
            """
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.configs.config_template import PostgresSQLAlchemyConfig
adapter = PostgresSQLAlchemyAdapter(PostgresSQLAlchemyConfig())
adapter.session_manager.engine.dispose()
""",
            "PostgresSQLAlchemyAdapter()",
        ),
        "sqlite": (
            """
from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter
from archipy.configs.config_template import SQLiteSQLAlchemyConfig
adapter = SQLiteSQLAlchemyAdapter(SQLiteSQLAlchemyConfig())
adapter.session_manager.engine.dispose()
""",
            "SQLiteSQLAlchemyAdapter()",
        ),
        "starrocks": (
            """
from archipy.adapters.starrocks.sqlalchemy.adapters import StarrocksSQLAlchemyAdapter
from archipy.configs.config_template import StarRocksSQLAlchemyConfig
adapter = StarrocksSQLAlchemyAdapter(StarRocksSQLAlchemyConfig())
adapter.session_manager.engine.dispose()
""",
            "StarrocksSQLAlchemyAdapter()",
        ),
        "minio": (
            """
from archipy.adapters.minio.adapters import MinioAdapter
from archipy.configs.config_template import MinioConfig
MinioAdapter(MinioConfig(ENDPOINT="localhost:9000", ACCESS_KEY="example", SECRET_KEY="example"))
""",
            "MinioAdapter()",
        ),
        "vault": (
            """
import os
from archipy.adapters.vault.adapters import VaultAdapter
from archipy.configs.config_template import VaultConfig
VaultAdapter(VaultConfig(ADDR=os.environ["BDD_VAULT_ADDR"], TOKEN=os.environ["BDD_VAULT_TOKEN"]))
""",
            "VaultAdapter()",
        ),
    }[package]
    environment = None
    if package == "vault":
        from archipy.configs.base_config import BaseConfig

        vault = BaseConfig.global_config().VAULT
        assert vault.ADDR and vault.TOKEN is not None
        environment = {
            **os.environ,
            "BDD_VAULT_ADDR": vault.ADDR,
            "BDD_VAULT_TOKEN": vault.TOKEN.get_secret_value(),
        }
    script = (
        "import sys\n"
        + setup
        + f"""
assert ("archipy.configs.base_config" in sys.modules) == (sys.version_info < (3, 15))

try:
    {default_constructor}
except AssertionError as error:
    assert "set global configs" in str(error)
else:
    raise AssertionError("Expected the default constructor to require global settings")
assert "archipy.configs.base_config" in sys.modules

from archipy.configs.base_config import BaseConfig
from archipy.models.runtime_settings import get_settings

settings = BaseConfig.model_construct()
BaseConfig.set_global(settings)
assert get_settings() is settings
"""
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
