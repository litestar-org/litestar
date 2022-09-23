# config

::: starlite.config.app.AppConfig
    options:
        members:
            - after_exception
            - after_request
            - after_response
            - after_shutdown
            - after_startup
            - allowed_hosts
            - before_request
            - before_send
            - before_shutdown
            - before_startup
            - cache_config
            - compression_config
            - cors_config
            - csrf_config
            - debug
            - dependencies
            - exception_handlers
            - guards
            - middleware
            - on_shutdown
            - on_startup
            - openapi_config
            - parameters
            - plugins
            - response_class
            - response_cookies
            - response_headers
            - route_handlers
            - security
            - static_files_config
            - tags
            - template_config

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
            - contact
            - create_examples
            - description
            - external_docs
            - license
            - openapi_controller
            - root_schema_site
            - security
            - servers
            - summary
            - tags
            - terms_of_service
            - title
            - use_handler_docstrings
            - version
            - webhooks
            - enabled_endpoints

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
