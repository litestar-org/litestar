# SQLAlchemy Plugin

::: starlite.plugins.sql_alchemy.SQLAlchemyPlugin
    options:
        members:
            - __init__
            - from_dict
            - from_pydantic_model_instance
            - get_pydantic_type
            - is_plugin_supported_type
            - on_app_init
            - providers_map
            - to_dict
            - to_pydantic_model_class

::: starlite.plugins.sql_alchemy.SQLAlchemyConfig
    options:
        members:
            - connection_string
            - create_async_engine
            - create_async_engine_callable
            - create_engine_callable
            - db_supports_json
            - dependency_key
            - engine_app_state_key
            - engine_config
            - session_class
            - session_config
            - session_maker
            - session_maker_app_state_key

::: starlite.plugins.sql_alchemy.SQLAlchemyEngineConfig
    options:
        members:
            - connect_args
            - echo
            - echo_pool
            - enable_from_linting
            - future
            - hide_parameters
            - isolation_level
            - json_deserializer
            - json_serializer
            - label_length
            - listeners
            - logging_level
            - logging_name
            - max_identifier_length
            - max_overflow
            - module
            - paramstyle
            - plugins
            - pool
            - pool_logging_name
            - pool_pre_ping
            - pool_recycle
            - pool_reset_on_return
            - pool_size
            - pool_timeout
            - pool_use_lifo
            - poolclass
            - query_cache_size
            - strategy

::: starlite.plugins.sql_alchemy.SQLAlchemySessionConfig
    options:
        members:
            - autocommit
            - autoflush
            - bind
            - binds
            - enable_baked_queries
            - expire_on_commit
            - future
            - info
            - query_cls
            - twophase
