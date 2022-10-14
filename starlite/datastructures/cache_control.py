from typing import ClassVar, Optional

from pydantic import BaseModel, Extra


class CacheControlHeader(BaseModel):
    CACHE_CONTROL_HEADER: ClassVar[str] = "cache-control"

    class Config:
        allow_population_by_field_name = True
        extra = Extra.forbid

        @classmethod
        def alias_generator(cls, field_name: str) -> str:
            return field_name.replace("_", "-")

    max_age: Optional[int] = None
    s_maxage: Optional[int] = None
    no_cache: Optional[bool] = None
    no_store: Optional[bool] = None
    private: Optional[bool] = None
    public: Optional[bool] = None
    no_transform: Optional[bool] = None
    must_revalidate: Optional[bool] = None
    proxy_revalidate: Optional[bool] = None
    must_understand: Optional[bool] = None
    immutable: Optional[bool] = None
    stale_while_revalidate: Optional[int] = None

    def to_header(self, include_header_name: bool = False) -> str:
        cc_items = []
        for key, value in self.dict(exclude_unset=True, exclude_none=True, by_alias=True).items():
            cc_items.append(key if isinstance(value, bool) else f"{key}={value}")

        return (f"{self.CACHE_CONTROL_HEADER}: " if include_header_name else "") + ", ".join(cc_items)

    @classmethod
    def prevent_storing(cls):
        return cls(no_store=True)
