# config

::: starlite.config.CacheConfig
    options:
        members:
            - backend
            - expiration
            - cache_key_builder

::: starlite.config.default_cache_key_builder

::: starlite.config.CORSConfig
    options:
        members:
            - allow_origins
            - allow_methods
            - allow_headers
            - allow_credentials
            - allow_origin_regex
            - expose_headers
            - max_age

::: starlite.config.CompressionBackend
    options:
        members:
            - GZIP
            - BROTLI

::: starlite.config.BrotliMode
    options:
        members:
            - GENERIC
            - TEXT
            - FONT

::: starlite.config.CompressionConfig
    options:
        members:
            - backend
            - minimum_size
            - gzip_compress_level
            - brotli_quality
            - brotli_mode
            - brotli_lgwin
            - brotli_lgblock
            - brotli_gzip_fallback

::: starlite.config.OpenAPIConfig
    options:
        members:
            - create_examples
            - openapi_controller
            - title
            - version
            - contact
            - description
            - external_docs
            - license
            - security
            - servers
            - summary
            - tags
            - terms_of_service
            - use_handler_docstrings
            - webhooks

::: starlite.config.StaticFilesConfig
    options:
        members:
            - path
            - directories
            - html_mode

::: starlite.config.TemplateConfig
    options:
        members:
            - directory
            - engine
            - engine_callback
