import re
from typing import Dict, List, Optional, Pattern, Union

from pydantic import BaseModel


class CORSConfig(BaseModel):
    """Configuration for CORS (Cross-Origin Resource Sharing).

    To enable CORS, pass an instance of this class to the [Starlite][starlite.app.Starlite] constructor using the
    'cors_config' key.
    """

    allow_origins: List[str] = ["*"]
    """
    List of origins that are allowed. Can use '*' in any component of the path, e.g. 'domain.*'. Sets the 'Access-Control-Allow-Origin' header.
    """
    allow_methods: List[str] = ["*"]
    """
    List of allowed HTTP methods. Sets the 'Access-Control-Allow-Methods' header.
    """
    allow_headers: List[str] = ["*"]
    """
    List of allowed headers. Sets the 'Access-Control-Allow-Headers' header.
    """
    allow_credentials: bool = False
    """
    Boolean dictating whether or not to set the 'Access-Control-Allow-Credentials' header.
    """
    allow_origin_regex: Optional[str] = None
    """
    Regex to match origins against.
    """
    expose_headers: List[str] = []
    """
    List of headers that are exposed via the 'Access-Control-Expose-Headers' header.
    """
    max_age: int = 600
    """
    Response aching TTL in seconds, defaults to 600. Sets the 'Access-Control-Max-Age' header.
    """
    exclude: Optional[Union[str, List[str]]] = None
    """
    An identifier to use on routes to disable authentication for a particular route.
    """
    exclude_opt_key: Optional[str] = None
    """
    A pattern or list of patterns to skip in the authentication middleware.
    """

    _compiled_regex: Pattern
    _is_allow_all_origins: bool
    _is_allow_all_methods: bool
    _is_allow_all_headers: bool
    _preflight_headers: Dict[str, str]

    @property
    def allowed_origins_regex(self) -> Pattern:
        """

        Returns:
            a compiled regex of the allowed path.
        """
        if not hasattr(self, "_compiled_regex"):
            origins = self.allow_origins
            if self.allow_origin_regex:
                origins.append(self.allow_origin_regex)
            self._compiled_regex = re.compile("|".join(origins))
        return self._compiled_regex

    @property
    def is_allow_all_origins(self) -> bool:
        """

        Returns:
            Boolean dictating whether all origins are allowed.
        """
        if not hasattr(self, "_is_allow_all_origins"):
            self._is_allow_all_origins = "*" in self.allow_origins
        return self._is_allow_all_origins

    @property
    def is_allow_all_methods(self) -> bool:
        """

        Returns:
            Boolean dictating whether all methods are allowed.
        """
        if not hasattr(self, "_is_allow_all_methods"):
            self._is_allow_all_methods = "*" in self.allow_methods
        return self._is_allow_all_methods

    @property
    def is_allow_all_headers(self) -> bool:
        """

        Returns:
            Boolean dictating whether all headers are allowed.
        """
        if not hasattr(self, "_is_allow_all_headers"):
            self._is_allow_all_headers = "*" in self.allow_headers
        return self._is_allow_all_headers

    @property
    def preflight_headers(self) -> Dict[str, str]:
        """

        Returns:
            A dictionary of headers to set on the response object.
        """
        if not hasattr(self, "_preflight_headers"):
            headers: Dict[str, str] = {"Access-Control-Max-Age": str(self.max_age)}
            if self.is_allow_all_origins:
                headers["Access-Control-Allow-Origin"] = "*"
            else:
                headers["Vary"] = "Origin"
            if self.allow_credentials:
                headers["Access-Control-Allow-Credentials"] = str(self.allow_credentials)
            if not self.is_allow_all_headers:
                headers["Access-Control-Allow-Headers"] = ", ".join(
                    {*self.allow_headers, "Accept", "Accept-Language", "Content-Language", "Content-Type"}
                )
            if "*" in self.allow_methods:
                headers["Access-Control-Allow-Methods"] = ", ".join(
                    self.allow_methods
                    if not self.is_allow_all_methods
                    else {"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}
                )
            self._preflight_headers = headers

        return self._preflight_headers

    def is_origin_allowed(self, origin: str) -> bool:
        """

        Args:
            origin: An origin header value.

        Returns:
            Boolean determining whether an origin is allowed.
        """
        return bool(self.is_allow_all_origins or self.allowed_origins_regex.fullmatch(origin))
