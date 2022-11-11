import re
from typing import Dict, List, Literal, Optional, Pattern, Union, cast

from pydantic import BaseModel, PrivateAttr, validator

from starlite.constants import DEFAULT_ALLOWED_CORS_HEADERS
from starlite.types import Empty, EmptyType, Method


class CORSConfig(BaseModel):
    """Configuration for CORS (Cross-Origin Resource Sharing).

    To enable CORS, pass an instance of this class to the [Starlite][starlite.app.Starlite] constructor using the
    'cors_config' key.
    """

    allow_origins: List[str] = ["*"]
    """
    List of origins that are allowed. Can use '*' in any component of the path, e.g. 'domain.*'. Sets the 'Access-Control-Allow-Origin' header.
    """
    allow_methods: List[Union[Literal["*"], "Method"]] = ["*"]
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

    _compiled_regex: Union[EmptyType, Pattern] = PrivateAttr(Empty)
    _is_allow_all_origins: Union[EmptyType, bool] = PrivateAttr(Empty)
    _is_allow_all_methods: Union[EmptyType, bool] = PrivateAttr(Empty)
    _is_allow_all_headers: Union[EmptyType, bool] = PrivateAttr(Empty)
    _preflight_headers: Union[EmptyType, Dict[str, str]] = PrivateAttr(Empty)
    _simple_headers: Union[EmptyType, Dict[str, str]] = PrivateAttr(Empty)

    @validator("allow_headers", always=True)
    def validate_allow_headers(cls, value: List[str]) -> List[str]:  # pylint: disable=no-self-argument
        """Ensure that the trusted hosts have correct domain wildcards.
        Args:
            value: A list of headers.

        Returns:
            A list of lower-cased headers.
        """
        return [v.lower() for v in value]

    @property
    def allowed_origins_regex(self) -> Pattern:
        """Get or create a compiled regex for allowed origins.

        Returns:
            A compiled regex of the allowed path.
        """
        if self._compiled_regex is Empty:
            origins = self.allow_origins
            if self.allow_origin_regex:
                origins.append(self.allow_origin_regex)
            setattr(
                self, "_compiled_regex", re.compile("|".join([origin.replace("*.", r".*\.") for origin in origins]))
            )
        return cast("Pattern", self._compiled_regex)

    @property
    def is_allow_all_origins(self) -> bool:
        """Get a cached boolean flag dictating whether all origins are allowed.

        Returns:
            Boolean dictating whether all origins are allowed.
        """
        if self._is_allow_all_origins is Empty:
            setattr(self, "_is_allow_all_origins", "*" in self.allow_origins)
        return cast("bool", self._is_allow_all_origins)

    @property
    def is_allow_all_methods(self) -> bool:
        """Get a cached boolean flag dictating whether all methods are allowed.

        Returns:
            Boolean dictating whether all methods are allowed.
        """
        if self._is_allow_all_methods is Empty:
            setattr(self, "_is_allow_all_methods", "*" in self.allow_methods)
        return cast("bool", self._is_allow_all_methods)

    @property
    def is_allow_all_headers(self) -> bool:
        """Get a cached boolean flag dictating whether all headers are allowed.

        Returns:
            Boolean dictating whether all headers are allowed.
        """
        if self._is_allow_all_headers is Empty:
            setattr(self, "_is_allow_all_headers", "*" in self.allow_headers)
        return cast("bool", self._is_allow_all_headers)

    @property
    def preflight_headers(self) -> Dict[str, str]:
        """Get cached pre-flight headers.

        Returns:
            A dictionary of headers to set on the response object.
        """
        if self._preflight_headers is Empty:
            headers: Dict[str, str] = {"Access-Control-Max-Age": str(self.max_age)}
            if self.is_allow_all_origins:
                headers["Access-Control-Allow-Origin"] = "*"
            else:
                headers["Vary"] = "Origin"
            if self.allow_credentials:
                headers["Access-Control-Allow-Credentials"] = str(self.allow_credentials).lower()
            if not self.is_allow_all_headers:
                headers["Access-Control-Allow-Headers"] = ", ".join(
                    sorted(set(self.allow_headers) | DEFAULT_ALLOWED_CORS_HEADERS)
                )
            if self.allow_methods:
                headers["Access-Control-Allow-Methods"] = ", ".join(
                    sorted(
                        set(self.allow_methods)
                        if not self.is_allow_all_methods
                        else {"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}
                    )
                )
            setattr(self, "_preflight_headers", headers)

        return cast("Dict[str, str]", self._preflight_headers)

    @property
    def simply_headers(self) -> Dict[str, str]:
        """Get cached simple headers.

        Returns:
            A dictionary of headers to set on the response object.
        """
        if self._simple_headers is Empty:
            self._simple_headers = {}
            if self.is_allow_all_origins:
                self._simple_headers["Access-Control-Allow-Origin"] = "*"
            if self.allow_credentials:
                self._simple_headers["Access-Control-Allow-Credentials"] = "true"
            if self.expose_headers:
                self._simple_headers["Access-Control-Expose-Headers"] = ", ".join(sorted(set(self.expose_headers)))
        return cast("Dict[str, str]", self._simple_headers)

    def is_origin_allowed(self, origin: str) -> bool:
        """Check whether a given origin is allowed.

        Args:
            origin: An origin header value.

        Returns:
            Boolean determining whether an origin is allowed.
        """
        return bool(self.is_allow_all_origins or self.allowed_origins_regex.fullmatch(origin))
