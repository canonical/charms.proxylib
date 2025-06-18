import os
from unittest import mock

import pytest

import jmodelproxylib
import jmodelproxylib.errors

DEFAULT_ENV = {
    "JUJU_CHARM_HTTPS_PROXY": "https://example.com:8080",
    "JUJU_CHARM_HTTP_PROXY": "http://example.com:8080",
    "JUJU_CHARM_NO_PROXY": "localhost,",
}


@pytest.mark.parametrize(
    "dropped",
    [
        "JUJU_CHARM_HTTPS_PROXY",
        "JUJU_CHARM_HTTP_PROXY",
        "JUJU_CHARM_NO_PROXY",
    ],
)
def test_raw_missing_juju_env(dropped):
    """Test that raw() raises JujuEnvironmentError if any required env var is missing."""
    env = DEFAULT_ENV.copy()
    env.pop(dropped)
    with mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(jmodelproxylib.errors.JujuEnvironmentError):
            jmodelproxylib.raw()


@pytest.mark.parametrize(
    "invalid",
    [
        "JUJU_CHARM_HTTPS_PROXY",
        "JUJU_CHARM_HTTP_PROXY",
    ],
)
def test_raw_invalid_juju_env(invalid):
    """Test that raw() raises ProxyUrlError if any http* env var is invalid."""
    env = DEFAULT_ENV.copy()
    env[invalid] = "not-a-valid-url"
    with mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(jmodelproxylib.errors.ProxyUrlError):
            jmodelproxylib.raw()


def test_raw_valid_juju_env():
    """Test that raw() returns the expected environment variables."""
    env = DEFAULT_ENV.copy()
    with mock.patch.dict(os.environ, env, clear=True):
        assert jmodelproxylib.raw() == env


@pytest.mark.parametrize(
    "expected,no_proxy",
    [
        ("127.0.0.1,localhost,::1,svc,svc.cluster,svc.cluster.local", "localhost"),
        ("127.0.0.1,localhost,::1,svc,svc.cluster,svc.cluster.local", ""),
        ("127.0.0.1,localhost,::1,svc,svc.cluster,svc.cluster.local,extra.com", "extra.com"),
        (
            "127.0.0.1,localhost,::1,svc,svc.cluster,svc.cluster.local,zzz.com,extra.com",
            "zzz.com,,extra.com",
        ),
    ],
    ids=[
        "doesn't duplicate no_proxy entries",
        "supplies an empty no_proxy",
        "adds to existing no_proxy entries",
        "doesn't sort user supplied order",
    ],
)
def test_validated_adds_no_proxies_in_front(no_proxy, expected):
    """Test that validated always adds extra no_proxies."""
    env = DEFAULT_ENV.copy()
    env["JUJU_CHARM_NO_PROXY"] = no_proxy
    K8S_DEFAULT_NO_PROXY = [
        "127.0.0.1",
        "localhost",
        "::1",
        "svc",
        "svc.cluster",
        "svc.cluster.local",
    ]
    with mock.patch.dict(os.environ, env, clear=True):
        validated = jmodelproxylib.validated(
            enabled=True,
            uppercase=False,
            add_no_proxies=K8S_DEFAULT_NO_PROXY,
        )
        assert validated == {
            "https_proxy": "https://example.com:8080",
            "http_proxy": "http://example.com:8080",
            "no_proxy": expected,
        }
