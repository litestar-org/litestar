# Guidelines

To contribute code changes or update the documentation, please follow these steps:

1. Fork the upstream repository and clone the fork locally.
2. Install [poetry](https://python-poetry.org/), and install the project's dependencies
   with `poetry install`.
3. Install [pre-commit](https://pre-commit.com/) and install the hooks by running `pre-commit install` in the
   repository's hook.
4. Make whatever changes and additions you wish and commit these - please try to keep your commit history clean.
5. Create a pull request to the main repository with an explanation of your changes. The PR should detail the
   contribution and link to any related issues - if existing.

## Code Contribution Guidelines

1. If you are adding or modifying existing code, please make sure to test everything you are doing. 100% test coverage
   is mandatory and tests should be well written.
2. All functions and methods should be documented with a doc string. The project uses the
   [Google style docstring](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html). If you come
   across a function or method that doesn't conform to this standard, please update it as you go.
3. If adding a new public interface to the library API ensure interface is included in the reference documentation and
   public members are listed, e.g.:

   ```text
   ::: starlite.config.CacheConfig
       options:
           members:
               - backend
               - expiration
               - cache_key_builder
   ```

4. Add or modify examples in the Docs related to the new functionality implemented. Please
   follow the guidelines in [Adding examples](#adding-examples)

## Project Documentation

The documentation is located under the `/doc` folder, with the `mkdocs.yml` file in the project root.

### Docs Theme and Appearance

We welcome contributions that enhance / improve the appearance and usability of the docs, as well as any images, icons
etc.

We use the excellent [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme, which comes with a lot
of options out of the box. If you wish to contribute to the docs style / setup, or static site generation, you should
consult the theme docs as a first step.

### Running the Docs Locally

To run the docs locally, simply use the `docker-compose` configuration in place by executing `docker compose up`.
On the first run it will pull and build the image, but afterwards this should be quite fast.

Note: if you want your terminal back use `docker compose up --detach` but then you will need to bring the docs down
with `docker compose down` rather than ctrl+C.

Another option is to build the docs locally: `poetry run tox -e docs`. The docs will reside under the `site/` directory.

### Writing and Editing Docs

We welcome contributions that enhance / improve the content of the docs. Feel free to add examples, clarify text,
restructure the docs etc. But make sure to follow these emphases:

- the docs should be as simple and easy to grasp as possible.
- the docs should be written in good idiomatic english.
- examples should be simple and clear.
- provide links where applicable.
- provide diagrams where applicable and possible.

#### Adding examples

The examples from the Docs are located in their own modules inside the
`examples/` folder. This makes it easier to test them alongside the rest of the
test suite, ensuring they do not become stale as Starlite evolves.

Please follow the next guidelines when adding a new example:

- Add the example in the corresponding module directory in `examples/` or create
  a new one if necessary
- Create a suite for the module in `examples/tests` that tests the facets of the
  example that it demonstrates
- Reference the example in the Markdown file with an external reference code
  block, e.g.

````md
```py title="Tests a Thing"
--8<-- "examples/test_thing.py"
```
````

#### Automatically execute examples

Our docs include an mkdocs hook that can automatically run requests against example apps
and include their result in the documentation page when its being built. This only requires 2 steps:

1. Create an example file with an `app` object in it, which is an instance of `Starlite`
2. Add a comment in the form of `# run: /hello` to the example file

When building the docs (or serving them locally), a process serving the `app` instance
will be launched, and the requests specified in the comments will be run against it. The
comments will be stripped from the result, and the output of the `curl` invocation inserted
after the example code-block.

The `# run: ` syntax is nothing special; Everything after the colon will be passed to
the `curl` command that's being invoked. The URL is being built automatically, so the
specified path can just be a path relative to the app.

In practice, this looks like the following:

```python
from typing import Dict

from starlite import Starlite, get


@get("/")
def hello_world() -> Dict[str, str]:
    """Handler function that returns a greeting dictionary."""
    return {"hello": "world"}


app = Starlite(route_handlers=[hello_world])

# run: /
```

This will produce the following markdown:

<pre>
```python
from typing import Dict

from starlite import Starlite, get


@get("/")
def hello_world() -> Dict[str, str]:
    """Handler function that returns a greeting dictionary."""
    return {"hello": "world"}


app = Starlite(route_handlers=[hello_world])
```

!!! example
    ```shell
    > curl http://127.0.0.1:8000/
    {"hello": "world"}
    ```
</pre>

#### Cleaning up examples

If you want to contribute to the ongoing effort of #343, you can use the `tools/doc_examples.py`
script to help you find and extract examples from the markdown files.

To find examples that need to be extracted invoke it:

`python tools/doc_examples.py check`

And then extract examples with `python tools/doc_examples.py extract /docs/path/to/file.md <destination folder>`

This will extract the inline examples from `/docs/path/to/file.md` into separate `.py`
files within `examples/<destination folder>`. Additionally, it will generate a test
scaffold, located in `examples/tests/<destination folder>`.

## Testing multiple python versions

Since the library needs to be compatible with older versions of python as well, it can be useful to run tests locally
against different python versions. To achieve this you can use the `tox` config that is included by doing the following.

1. Install [pyenv](https://github.com/pyenv/pyenv).
2. Install required python versions via pyenv, e.g., `$ pyenv install 3.x.x` for each required version.
3. In root directory of library, create .python-version file in root.
4. Restart shell.
5. Remove any existing poetry environment: `$ poetry env remove python`
6. Tell poetry to use system python: `$ poetry env use system`
7. Install the dependencies `$ poetry install`

### Tox Commands

- Run: `$ poetry run tox`
- Force recreate tox environments: `$ poetry run tox -r`
- Run specific tox environment: `$ poetry run tox -e py37`
- Run all pre-commit checks: `$ poetry run tox -e all-checks`
  - Run on specific files/directories: `$ poetry run tox -e all-checks starlite/cache/**`
- Run pylint from pre-commit: `$ poetry run tox -e lint`
  - Run on specific files/directories: `$ poetry run tox -e lint starlite/cache/**`
- Run formatting pre-commit hooks: `$ poetry run tox -e fmt`
- Run type-check from pre-commit: `$ poetry run tox -e typecheck`
- Build docs locally: `$ poetry run tox -e docs`

Note that these commands may be quite slow to run the first time as environments are created and dependencies installed,
but subsequent runs should be much faster.

### Checking test coverage

You can check the unit test coverage by running: `$ poetry run pytest tests examples --cov=starlite --cov=examples`

Coverage should be 100% for any code you touch. Note that coverage will also be reported on your PR by the `SonarCloud`
tool.

## Release workflow (Maintainers only)

1. Update changelog.md
2. Increment the version in pyproject.toml.
3. Commit and push.
4. In GitHub go to the releases tab
5. Pick "draft a new release"
6. Give it a title and a tag, both vX.X.X
7. Fill in the release description, you can let GitHub do it for you and then edit as needed.
8. Publish the release.
9. look under the action pane and make sure the release action runs correctly
