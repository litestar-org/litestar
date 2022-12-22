# CLI

Starlite optionally provides a simple command line interface, for running and managing
Starlite applications, powered by [click](https://click.palletsprojects.com/) and
[rich](https://rich.readthedocs.io).

## Enabling the CLI

Dependencies for the CLI are not included by default, to keep the packages needed to install
Starlite to a minimum. To enable the CLI, Starlite has to be installed with the `cli` or `standard`
extra:

```shell
pip install starlite[cli]
```

```shell
pip install starlite[standard]
```

After installing any of these two, the `starlite` command will be available as the entrypoint
to the CLI.

## Autodiscovery

Starlite will automatically discover Starlite applications in certain places:

- `app.py`
- `application.py`
- `asgi.py`
- `app/__init__.py`

If any of these files contains an instance of the `Starlite` class, the CLI will pick it up.


## Commands

### Starlite

The `starlite` command is the main entrypoint to the CLI. If the `--app` flag is not passed,
the app will be automatically discovered as described in [the section above](#autodiscovery)

#### Options

| Flag             | Environment variable | Description                                                                       |
|------------------|----------------------|-----------------------------------------------------------------------------------|
| `--app`          | `STARLITE_APP`       | Module path to the app in the format of `<modulename>.<submodule>:<app instance>` |


#### Run

The `run` command runs a Starlite application using [uvicorn](https://www.uvicorn.org/).

```shell
starlite run
```

!!! warning
    This feature is intended for development purposes only and should not be used to
    deploy production applications


<!-- markdownlint-disable -->
##### Options
<!-- markdownlint-restore -->

| Flag             | Environment variable | Description                                                                       |
|------------------|----------------------|-----------------------------------------------------------------------------------|
| `-r`, `--reload` | `STARLITE_RELOAD`    | Reload the application when files in its directory are changed                    |
| `-p`, `--port`   | `STARLITE_PORT`      | Bind the the server to this port [default: 8000]                                  |
| `--host`         | `STARLITE_HOST`      | Bind the server to this host [default: 127.0.0.1]                                 |
| `--debug`        | `STARLITE_DEBUG`     | Run the application in debug mode                                                 |
| `--app`          | `STARLITE_APP`       | Module path to the app in the format of `<modulename>.<submodule>:<app instance>` |


#### Info

The `info` command displays useful information about the selected application and its configuration

```shell
starlite info
```

![starlite info](/starlite/images/cli/starlite_info.png)


#### Routes

The `routes` command displays a tree view of the routing table

```shell
starlite routes
```

![starlite info](/starlite/images/cli/starlite_routes.png)


#### Sessions

This command and its subcommands provide management utilities for
[server-side session backends](/starlite/usage/7-middleware/3-builtin-middlewares/5-session-middleware/#server-side-sessions).


##### Delete

The `delete` subcommand deletes a specific session from the backend.

```shell
starlite sessions delete cc3debc7-1ab6-4dc8-a220-91934a473717
```

##### Clear

The `clear` subcommand clears all sessions from the backend.

```shell
starlite sessions clear
```
