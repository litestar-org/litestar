# SQLAlchemy Plugin

Starlite come with built-in support for [SQLAlchemy](https://docs.sqlalchemy.org/) via
the[`SQLAlchemyPlugin`][starlite.plugins.sql_alchemy.SQLAlchemyPlugin].

## Features

- Managed [sessions](https://docs.sqlalchemy.org/en/14/orm/session.html) (sync and async) including dependency injection
- Automatic serialization of SQLAlchemy models powered pydantic
- Data validation based on SQLAlchemy models powered pydantic

!!! info
    The following examples use SQLAlchemy's "2.0 Style" introduced in SQLAlchemy 1.4.

    If you are unfamiliar with it, you can find a comprehensive migration guide in SQLAlchemy's
    documentation [here](https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#what-s-new-in-sqlalchemy-1-4),
    and [a handy table](https://docs.sqlalchemy.org/en/14/changelog/migration_20.html#migration-orm-usage)
    comparing the ORM usage

!!! important
    The `SQLAlchemyPlugin` supports only
    [mapped classes](https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#declaring-mapped-classes).
    [Tables](https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#setting-up-metadata-with-table-objects) are currently
    not supported since they aren't easily converted to pydantic models.

## Basic Use

You can simply pass an instance of `SQLAlchemyPlugin` without passing config to the Starlite constructor. This will
extend support for serialization, deserialization and DTO creation for SQLAlchemy declarative models:

=== "Async"

    ```py title="sqlalchemy_plugin.py"
    --8<-- "examples/plugins/sqlalchemy_plugin/sqlalchemy_async.py"
    ```

=== "Sync"

    ```py title="sqlalchemy_plugin.py"
    --8<-- "examples/plugins/sqlalchemy_plugin/sqlalchemy_sync.py"
    ```

!!! Example "Using imperative mappings"
    [Imperative mappings](https://docs.sqlalchemy.org/en/14/orm/mapping_styles.html#imperative-mapping)
    are supported as well, just make sure to use a mapped class instead of the table itself
    ```python
    company_table = Table(
        "company",
        Base.registry.metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
        Column("worth", Float),
    )


    class Company:
        pass


    Base.registry.map_imperatively(Company, company_table)
    ```

## Relationships

!!! important
    Currently only to-one relationships are supported because of the way the SQLAlchemy plugin handles relationships.
      Since it recursively traverses relationships, a cyclic reference will result in an endless loop. To prevent this,
      these relationships will be type as `Any` in the pydantic model

!!! important
    Relationships are typed as `Optional` in the pydantic model by default so sending incomplete models won't cause any issues

### Simple relationships

Simple relationship can be handled by the plugin automatically:

```py title="sqlalchemy_relationships.py"
--8<-- "examples/plugins/sqlalchemy_plugin/sqlalchemy_relationships.py"
```

!!! example "In action"
    Run the above with `uvicorn sqlalchemy_relationships:app`, navigate your browser to `http://127.0.0.0:8000/user/1`
    and you will see:

    ```json
    {
      "id": 1,
      "name": "Peter",
      "company_id": 1,
      "company": {
        "id": 1,
        "name": "Peter Co.",
        "worth": 0
      }
    }
    ```

### To-Many relationships and circular references

For to-many relationships or those that contain circular references you need to define the pydantic models yourself:

```py title="sqlalchemy_relationships_to_many"
--8<-- "examples/plugins/sqlalchemy_plugin/sqlalchemy_relationships_to_many.py"
```

!!! example "In action"
    Run the above with `uvicorn sqlalchemy_relationships_to_many:app`, navigate your browser to `http://127.0.0.0:8000/user/1`
    and you will see:

    ```json
    {
      "id": 1,
      "name": "Peter",
      "pets": [
        {
          "id": 1,
          "name": "Paul"
        }
      ]
    }
    ```

## Configuration

You can configure the Plugin using the `SQLAlchemyPluginConfig` object. See the API Reference for a full
list all the options available on [SQLAlchemyConfig][starlite.plugins.sql_alchemy.SQLAlchemyConfig].
