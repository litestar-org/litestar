# Compression

HTML responses can optionally be compressed. Starlite has built in support for gzip and brotli. Gzip support is provided through the built-in Starlette classes, and brotli support can be added by installing the `brotli` extras.

You can enable either backend by passing an instance of `starlite.config.CompressionConfig` into the `compression_config` application parameter.

## GZIP

You can enable gzip compression of responses by passing an instance of `starlite.config.CompressionConfig` with the `backend` parameter set to `"gzip"`:

You can configure the following additional gzip-specific values:

- `minimum_size`: the minimum threshold for response size to enable compression. Smaller responses will not be compressed. Defaults is `500`, i.e. half a kilobyte.
- `gzip_compress_level`: a range between 0-9, see the [official python docs](https://docs.python.org/3/library/gzip.html). Defaults to `9`, which is the maximum value.

```python
from starlite import Starlite, CompressionConfig

app = Starlite(
    request_handlers=[...],
    compression_config=CompressionConfig(backend="gzip", gzip_compress_level=9),
)
```

## Brotli

The Brotli package is required to run this middleware. It is available as an extras to starlite with the `brotli` extra. (`pip install starlite[brotli]`)

You can enable brotli compression of responses by passing an instance of `starlite.config.CompressionConfig` with the `backend` parameter set to `"brotli"`:

You can configure the following additional brotli-specific values:

- `minimum_size`: the minimum threshold for response size to enable compression. Smaller responses will not be compressed. Defaults is `500`, i.e. half a kilobyte.
- `brotli_quality`: Range [0-11], Controls the compression-speed vs compression-density tradeoff. The higher the quality, the slower the compression.
- `brotli_mode`: The compression mode can be MODE_GENERIC (default), MODE_TEXT (for UTF-8 format text input) or MODE_FONT (for WOFF 2.0).
- `brotli_lgwin`: Base 2 logarithm of size. Range is 10 to 24. Defaults to 22.
- `brotli_lgblock`: Base 2 logarithm of the maximum input block size. Range is 16 to 24. If set to 0, the value will be set based on the quality. Defaults to 0.
- `brotli_gzip_fallback`: a boolean to indicate if gzip should be used if brotli is not supported.

```python
from starlite import Starlite
from starlite.config import CompressionConfig

app = Starlite(
    request_handlers=[...],
    compression_config=CompressionConfig(backend="brotli", brotli_gzip_fallback=True),
)
```
