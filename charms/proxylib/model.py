import logging
import os
from typing import TypeAlias
from urllib.parse import urlparse

import charms.proxylib.errors as errors

Env: TypeAlias = dict[str, str]
log = logging.getLogger(__name__)


def _validate_proxy_url(url: str) -> None:
    """Check if the given URL is valid for use as a proxy.

    Args:
        url (str):            The URL to validate.
    Raises:
        ProxyUrlError: If the URL is malformed or does not
                       conform to expected proxy URL formats.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise errors.ProxyUrlError(
            f"Invalid proxy URL: {url=}. Only 'http' and 'https' schemes are supported."
        )
    elif not parsed.hostname and not parsed.netloc:
        raise errors.ProxyUrlError(
            f"Invalid proxy URL: {url=}. It must include a valid hostname or netloc."
        )


def raw() -> Env:
    """Get the raw proxy settings from the environment.

    Raises:
        JujuEnvironmentError: If any of the required environment variables are not set.
        ProxyUrlError: If the proxy URLs are malformed or do not conform to expected formats.
    """
    proxy_env_keys = [
        "JUJU_CHARM_HTTPS_PROXY",
        "JUJU_CHARM_HTTP_PROXY",
        "JUJU_CHARM_NO_PROXY",
    ]

    s: Env = {}
    for k in proxy_env_keys:
        if (v := os.getenv(k)) is None:
            raise errors.JujuEnvironmentError(f"{k} environment variable is not set.")
        s[k] = v.strip()
        if v and k in ("JUJU_CHARM_HTTP_PROXY", "JUJU_CHARM_HTTPS_PROXY"):
            _validate_proxy_url(v)
    return s


def validated(
    enabled: bool,
    uppercase: bool = True,
    add_no_proxies: list[str] = [],
) -> Env:
    """Get the validated proxy settings from the environment.

    This function retrieves the raw proxy settings from the environment.
    It validates the proxy URLs to ensure they conform to expected formats.

    It converts the JUJU environment variables for HTTP and HTTPS proxies
    into a dictionary format suitable for use in applications that require
    proxy settings with the keys "http_proxy" and "https_proxy" and "no_proxy".

    Args:
        enabled (bool):   If True, enable the proxy settings.
                          If False, return an empty dictionary.
        uppercase (bool): If True, add the uppercase keys as well
                          If False, only the lowercase keys
        add_no_proxies (list[str]): Additional entries to add to the no_proxy list.
    """

    if not enabled:
        log.debug("Proxy disabled, using empty settings.")
        return {}
    s = raw()
    http_proxy = s["JUJU_CHARM_HTTP_PROXY"]
    https_proxy = s["JUJU_CHARM_HTTPS_PROXY"]
    env_no_proxy = s["JUJU_CHARM_NO_PROXY"]
    uniq_seen = dict.fromkeys(add_no_proxies + env_no_proxy.split(","))
    no_proxy = ",".join(filter(None, uniq_seen))

    norm = {"https_proxy": https_proxy, "http_proxy": http_proxy, "no_proxy": no_proxy}
    if uppercase:
        norm.update({k.upper(): v for k, v in norm.items()})
    return norm
