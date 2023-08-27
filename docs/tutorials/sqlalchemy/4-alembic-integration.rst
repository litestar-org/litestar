Database migrations with Alembic
--------------------------------

Now that we've configured our example application with the :class:`SQLAlchemyPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemyPlugin>` plugin, we now have an additional ``database`` command when we run the ``litestar`` CLI application.

This sub-command of the Litestar CLI enables easy to use integration with the ``Alembic`` migrations.

Initializing Migrations
=======================

To get started, we will need to initialize the Alembic templates for our project.

    .. code-block:: shell

        litestar database init

This will create a ``migrations`` folder in the root of your project.


Create Migrations
=================

Now that we've initialized migrations in our project, we are ready to generate our first migration!

    .. code-block:: shell

        litestar database make-migrations

Running this command will introspect your database and loaded models to create a migration file in the ``./migrations/versions`` folder.


Upgrade Database Schema
=======================

The last step is to apply the schema changes to the database.

    .. code-block:: shell

        litestar database upgrade

Congratulations!  You've now applied all schema changes to your database.  If this is the first time running the command, it will create all new objects.  Otherwise, Alembic will detect your current revision and upgrade from there.

Schema Changes
==============

As your database model change over time, you will want to re-run the ``make-migrations`` command to generate new change revision and applying the changes.

    .. code-block:: shell

        litestar database make-migrations
        litestar database upgrade



Next steps
==========

Our example application is really taking shape!

In our latest update, we demonstrated how to use the ``Alembic`` database migrations plugin:

1. We initialized Alembic for our project
2. We generated a new Alembic revision for our database models
3. We applied those changes to our database.

Take a few minutes to run ``litestar database``.  All current Alembic commands are exposed:

    .. code-block:: shell

        ❯ litestar database
        Using Litestar app from env: 'app.asgi:create_app'

        Usage: litestar database [OPTIONS] COMMAND [ARGS]...

        Manage SQLAlchemy database components.

        ╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
        │ --help  -h    Show this message and exit.                                                        │
        ╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────╮
        │ downgrade              Downgrade database to a specific revision.                                │
        │ init                   Initialize migrations for the project.                                    │
        │ make-migrations        Create a new migration revision.                                          │
        │ merge-migrations       Merge multiple revisions into a single new revision.                      │
        │ show-current-revision  Shows the current revision for the database.                              │
        │ stamp-migration        Mark (Stamp) a specific revision as current without applying the          │
        │                        migrations.                                                               │
        │ upgrade                Upgrade database to a specific revision.                                  │
        ╰──────────────────────────────────────────────────────────────────────────────────────────────────╯

Next up, we'll make one final change to our application, and then we'll be recap!
