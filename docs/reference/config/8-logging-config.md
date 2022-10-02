# Logging Config

::: starlite.config.logging.BaseLoggingConfig
    options:
        members:
            - configure

::: starlite.config.logging.LoggingConfig
    options:
        members:
            - disable_existing_loggers
            - filters
            - formatters
            - handlers
            - incremental
            - loggers
            - propagate
            - root

::: starlite.config.logging.StructLoggingConfig
    options:
        members:
            - cache_logger_on_first_use
            - context_class
            - logger_factory
            - processors
            - wrapper_class
