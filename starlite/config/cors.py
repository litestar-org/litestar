from typing import List, Optional

from pydantic import BaseModel


class CORSConfig(BaseModel):
    """Configuration for CORS (Cross-Origin Resource Sharing).

    To enable CORS, pass an instance of this class to the
    [Starlite][starlite.app.Starlite] constructor using the
    'cors_config' key.
    """

    allow_origins: List[str] = ["*"]
    """
        List of origins that are allowed. Can use '*' in any component of the path, e.g. 'domain.*'.
        Sets the 'Access-Control-Allow-Origin' header.
    """
    allow_methods: List[str] = ["*"]
    """
        List of allowed HTTP methods.
        Sets the 'Access-Control-Allow-Methods' header.
    """
    allow_headers: List[str] = ["*"]
    """
        List of allowed headers.
        Sets the 'Access-Control-Allow-Headers' header.
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
        Response aching TTL in seconds, defaults to 600.
        Sets the 'Access-Control-Max-Age' header.
    """
