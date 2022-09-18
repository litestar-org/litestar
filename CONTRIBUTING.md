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
2. All public functions and methods should be documented with a doc string. The project uses
   the [Google style docstring](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).
   Private methods should have a doc string explaining what they do, but do not require an elaborate doc string.
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

### Writing and Editing Docs

We welcome contributions that enhance / improve the content of the docs. Feel free to add examples, clarify text,
restructure the docs etc. But make sure to follow these emphases:

- the docs should be as simple and easy to grasp as possible.
- the docs should be written in good idiomatic english.
- examples should be simple and clear.
- provide links where applicable.
- provide diagrams where applicable and possible.

## Testing multiple python versions

Since the library needs to be compatible with older versions of python as well, it can be useful to run tests locally
against different python versions. To achieve this you can use the `tox` config that is included by doing the following.

1. Install [pyenv](https://github.com/pyenv/pyenv).
2. Install required python versions via pyenv, e.g., `$ pyenv install 3.x.x` for each required version.
3. In root directory of library, create .python-version file in root.
4. Restart shell.
5. Remove any existing poetry environment: `$ poetry env remove python`
6. Tell poetry to use system python: `$ poetry env use system`
7. Install the dependencies `$ poetry install --extras testing`

### Tox Commands

- Run: `$ poetry run tox`
- Force recreate tox environments: `$ poetry run tox -r`
- Run specific tox environment: `$ poetry run tox -e py37`
- Run pre-commit only: `$ poetry run tox -e lint`

Note that these commands may be quite slow to run the first time as environments are created and dependencies installed,
but subsequent runs should be much faster.

### Checking test coverage

You can check the unit test coverage by running: `$ poetry run pytest tests examples --cov=.`

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
