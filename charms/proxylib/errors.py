class LibraryError(Exception):
    """Base class for all exceptions raised by the charms.proxylib library."""

    pass


class ProxyUrlError(LibraryError):
    """Custom exception for invalid proxy URLs."""

    pass


class JujuEnvironmentError(LibraryError):
    """Custom exception for invalid juju environment variable."""

    pass
