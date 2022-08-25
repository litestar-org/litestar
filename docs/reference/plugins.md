# plugins

::: starlite.plugins.base.PluginProtocol
    options:
        members:
            - on_app_init
            - is_plugin_supported_type
            - to_pydantic_model_class
            - from_pydantic_model_instance
            - to_dict
            - from_dict

::: starlite.plugins.piccolo_orm.PiccoloORMPlugin

::: starlite.plugins.sql_alchemy.SQLAlchemyPlugin

::: starlite.plugins.tortoise_orm.TortoiseORMPlugin
