import os
from unittest import mock

import pytest
from lightkube.models.core_v1 import EnvVar

import charms.proxylib
import charms.proxylib.errors

DEFAULT_ENV = {
    "JUJU_CHARM_HTTPS_PROXY": "https://example.com:8080",
    "JUJU_CHARM_HTTP_PROXY": "http://example.com:8080",
    "JUJU_CHARM_NO_PROXY": "localhost,",
}


def test_environ_disabled():
    """Test that environ() returns an empty dict when no proxy settings are set."""
    env = DEFAULT_ENV.copy()
    with mock.patch.dict(os.environ, env, clear=True):
        environ = charms.proxylib.environ(enabled=False)
    assert environ == {}
    assert environ.error is None


@pytest.mark.parametrize(
    "empty, available",
    [
        ["JUJU_CHARM_HTTPS_PROXY", "HTTP_PROXY"],
        ["JUJU_CHARM_HTTP_PROXY", "HTTPS_PROXY"],
    ],
)
def test_environ_empty_http_value(empty, available, caplog):
    caplog.set_level("ERROR", logger="charms.proxylib")
    env = DEFAULT_ENV.copy()
    env[empty] = ""
    with mock.patch.dict(os.environ, env, clear=True):
        environ = charms.proxylib.environ(enabled=True)
    assert environ[available]
    assert environ[available.lower()]
    assert environ[empty[11:]] == ""
    assert environ[empty[11:].lower()] == ""
    assert environ["no_proxy"] == "localhost"
    assert environ["NO_PROXY"] == "localhost"
    assert not environ.error, "Should not be in error state"


@pytest.mark.parametrize(
    "invalid",
    [
        "JUJU_CHARM_HTTPS_PROXY",
        "JUJU_CHARM_HTTP_PROXY",
    ],
)
def test_environ_invalid_scheme(invalid, caplog):
    caplog.set_level("ERROR", logger="charms.proxylib")
    env = DEFAULT_ENV.copy()
    env[invalid] = "not-a-valid-url"
    with mock.patch.dict(os.environ, env, clear=True):
        environ = charms.proxylib.environ(enabled=True)
    assert environ == {}
    assert environ.error, "Should be in error state"
    assert environ.error.startswith("Invalid proxy URL: url='not-a-valid-url'")
    assert environ.error.endswith("Only 'http' and 'https' schemes are supported.")
    assert caplog.messages == [
        "Error retrieving proxy settings: Invalid proxy URL: url='not-a-valid-url'. "
        "Only 'http' and 'https' schemes are supported."
    ]


@pytest.mark.parametrize(
    "invalid",
    [
        "JUJU_CHARM_HTTPS_PROXY",
        "JUJU_CHARM_HTTP_PROXY",
    ],
)
def test_environ_invalid_location(invalid, caplog):
    caplog.set_level("ERROR", logger="charms.proxylib")
    env = DEFAULT_ENV.copy()
    env[invalid] = "http://"
    with mock.patch.dict(os.environ, env, clear=True):
        environ = charms.proxylib.environ(enabled=True)
    assert environ == {}
    assert environ.error, "Should be in error state"
    assert environ.error.startswith("Invalid proxy URL: url='http://'")
    assert environ.error.endswith("It must include a valid hostname or netloc.")
    assert caplog.messages == [
        "Error retrieving proxy settings: Invalid proxy URL: url='http://'. "
        "It must include a valid hostname or netloc."
    ]


def test_environ_lowercase_only():
    """Test that environ() returns the expected environment variables in lowercase."""
    env = DEFAULT_ENV.copy()
    with mock.patch.dict(os.environ, env, clear=True):
        environ = charms.proxylib.environ(enabled=True, uppercase=False)
    assert environ == {
        "https_proxy": "https://example.com:8080",
        "http_proxy": "http://example.com:8080",
        "no_proxy": "localhost",
    }
    assert environ.error is None


def test_environ_called():
    """Test that environ() returns the expected environment variables in lowercase."""
    env = DEFAULT_ENV.copy()
    with mock.patch.dict(os.environ, env, clear=True):
        environ = charms.proxylib.environ(enabled=True)
    assert environ == {
        "HTTPS_PROXY": "https://example.com:8080",
        "HTTP_PROXY": "http://example.com:8080",
        "NO_PROXY": "localhost",
        "https_proxy": "https://example.com:8080",
        "http_proxy": "http://example.com:8080",
        "no_proxy": "localhost",
    }
    assert environ.error is None


def test_environ_context():
    """Test that environ() can be used as a context manager."""
    env = DEFAULT_ENV.copy()
    env["HTTP_PROXY"] = "http://original.com:8080"
    with mock.patch.dict(os.environ, env, clear=True):
        with charms.proxylib.environ(enabled=True) as env:
            assert env == {
                "HTTPS_PROXY": "https://example.com:8080",
                "HTTP_PROXY": "http://example.com:8080",
                "NO_PROXY": "localhost",
                "https_proxy": "https://example.com:8080",
                "http_proxy": "http://example.com:8080",
                "no_proxy": "localhost",
            }
            assert env.error is None
        # After exiting the context, the original environment should remain unchanged
        assert os.environ.get("HTTPS_PROXY") is None
        assert os.environ.get("HTTP_PROXY") == "http://original.com:8080"
        assert os.environ.get("NO_PROXY") is None


def test_systemd_no_juju_app():
    """Test that view.systemd fails without a JUJU_UNIT_NAME."""
    env = DEFAULT_ENV.copy()
    env["JUJU_UNIT_NAME"] = "test/0"
    with pytest.raises(charms.proxylib.errors.JujuEnvironmentError):
        env = charms.proxylib.environ(env, enabled=True)
        charms.proxylib.systemd(env, "testd")


def test_systemd_enabled():
    """Test that environ() can be used to write a systemd unit."""
    env = DEFAULT_ENV.copy()
    env["JUJU_UNIT_NAME"] = "test/0"
    with mock.patch.dict(os.environ, env, clear=True):
        env = charms.proxylib.environ(enabled=True)
        content = charms.proxylib.systemd(env, "testd")
        assert content == (
            """[Service]
# Autogenerated by juju_app='test' for service='testd'
Environment="http_proxy=http://example.com:8080"
Environment="HTTP_PROXY=http://example.com:8080"
Environment="https_proxy=https://example.com:8080"
Environment="HTTPS_PROXY=https://example.com:8080"
Environment="no_proxy=localhost"
Environment="NO_PROXY=localhost"
"""
        )


def test_systemd_disabled():
    """Test that environ() can be used to empty a systemd unit."""
    env = DEFAULT_ENV.copy()
    env["JUJU_UNIT_NAME"] = "test/0"
    with mock.patch.dict(os.environ, env, clear=True):
        env = charms.proxylib.environ(enabled=False)
        content = charms.proxylib.systemd(env, "testd")
        assert content == ""


def test_container_vars():
    """Test that environ() can be used to write container environment variables."""
    env = DEFAULT_ENV.copy()
    with mock.patch.dict(os.environ, env, clear=True):
        content = charms.proxylib.container_vars(charms.proxylib.environ(env, enabled=True))
    assert content == [
        EnvVar(name="http_proxy", value="http://example.com:8080"),
        EnvVar(name="HTTP_PROXY", value="http://example.com:8080"),
        EnvVar(name="https_proxy", value="https://example.com:8080"),
        EnvVar(name="HTTPS_PROXY", value="https://example.com:8080"),
        EnvVar(name="no_proxy", value="localhost"),
        EnvVar(name="NO_PROXY", value="localhost"),
    ]


def test_container_vars_no_lightkube():
    import importlib
    import sys

    with mock.patch.dict(sys.modules, {"lightkube.models.core_v1": None}):
        # Remove the module under test from sys.modules to force a fresh import
        for k in dict(sys.modules).keys():
            if k.startswith("charms.proxylib"):
                sys.modules.pop(k)
        import charms.proxylib

        importlib.reload(charms.proxylib)

    env = DEFAULT_ENV.copy()
    with pytest.raises(NotImplementedError):
        # This should raise an error because lightkube is not available
        with mock.patch.dict(os.environ, env, clear=True):
            charms.proxylib.container_vars(charms.proxylib.environ(env, enabled=True))
