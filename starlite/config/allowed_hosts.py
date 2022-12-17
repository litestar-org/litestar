from typing import List, Optional, Union

from pydantic import BaseModel, validator

from starlite.types import Scopes


class AllowedHostsConfig(BaseModel):
    """Configuration for allowed hosts protection.

    To enable allowed hosts protection, pass an instance of this class to the [Starlite][starlite.app.Starlite]
    constructor using the 'allowed_hosts' key.
    """

    allowed_hosts: List[str] = ["*"]
    """A list of trusted hosts.

    Use '*' to allow all hosts, or prefix domains with '*.' to allow all sub domains.
    """
    exclude: Optional[Union[str, List[str]]] = None
    """A pattern or list of patterns to skip in the Allowed Hosts middleware."""
    exclude_opt_key: Optional[str] = None
    """An identifier to use on routes to disable hosts check for a particular route."""
    scopes: Optional[Scopes] = None
    """ASGI scopes processed by the middleware, if None both 'http' and 'websocket' will be processed."""
    www_redirect: bool = True
    """A boolean dictating whether to redirect requests that start with 'www.' and otherwise match a trusted host."""

    @validator("allowed_hosts", always=True)
    def validate_allowed_hosts(cls, value: List[str]) -> List[str]:  # pylint: disable=no-self-argument
        """Ensure that the trusted hosts have correct domain wildcards.

        Args:
            value: A list of trusted hosts.

        Returns:
            A list of trusted hosts.
        """
        for host in value:
            if host != "*" and "*" in host and not host.startswith("*."):
                raise ValueError(
                    "domain wildcards can only appear in the beginning of the domain, e.g. '*.example.com'"
                )
        return value
