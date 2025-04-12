from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig, SQLAlchemyPlugin

sqlalchemy_config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///test.sqlite")
plugin = SQLAlchemyPlugin(config=sqlalchemy_config)
