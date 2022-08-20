# config

::: starlite.config.cache.CacheConfig
    options:
        members:
            - backend
            - expiration
            - cache_key_builder
            - to_cache

::: starlite.config.cache.default_cache_key_builder

::: starlite.config.cors.CORSConfig
    options:
        members:
            - allow_origins
            - allow_methods
            - allow_headers
            - allow_credentials
            - allow_origin_regex
            - expose_headers
            - max_age

::: starlite.config.csrf.CSRFConfig
    options:
        members:
            - secret
            - cookie_name
            - cookie_path
            - header_name
            - cookie_secure
            - cookie_httponly
            - cookie_samesite
            - cookie_domain
            - safe_methods

::: starlite.config.compression.CompressionConfig
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

::: starlite.config.openapi.OpenAPIConfig
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

::: starlite.config.static_files.StaticFilesConfig
    options:
        members:
            - path
            - directories
            - html_mode

::: starlite.config.template.TemplateConfig
    options:
        members:
            - directory
            - engine
            - engine_callback
