"""Step definitions for optional dependency scenarios."""

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
