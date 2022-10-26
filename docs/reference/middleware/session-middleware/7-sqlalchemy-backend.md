# SQLAlchemy backends

::: starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend
    options:
        members:
            - __init__
            - delete_expired

::: starlite.middleware.session.sqlalchemy_backend.SQLAlchemyBackend
    options:
        members:
            - __init__
            - get
            - set
            - delete
            - delete_all
            - delete_expired

::: starlite.middleware.session.sqlalchemy_backend.AsyncSQLAlchemyBackend
    options:
        members:
            - __init__
            - get
            - set
            - delete
            - delete_all
            - delete_expired

::: starlite.middleware.session.sqlalchemy_backend.SQLAlchemyBackendConfig
    options:
        members:
            - models
            - plugin

::: starlite.middleware.session.sqlalchemy_backend.create_session_model

::: starlite.middleware.session.sqlalchemy_backend.register_session_model

::: starlite.middleware.session.sqlalchemy_backend.SessionModelMixin
    options:
        members:
            - session_id
            - data
            - expires
            - expired

::: starlite.middleware.session.sqlalchemy_backend.SessionModel
    options:
        members:
            - __tablename__
            - id
