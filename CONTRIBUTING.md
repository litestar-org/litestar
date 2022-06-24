# Contributing

To contribute code changes or update the documentation, please follow these steps:

## Making changes

1. Fork the upstream repository and clone the fork locally.
2. Setup a development environment by follwing the steps below.
3. Make whatever changes and additions you wish and commit these - please try to keep your commit history clean.
4. Create a pull request to the main repository with an explanation of your changes

Note: if you add new code or modify existing code - 100% test coverage is mandatory and tests should be well written.

## Setup a simple dev environment

1. Ensure `poetry` is available

## Setup a dev environment

1. Install `pyenv` and configure per the instructions for your platform: https://github.com/pyenv/pyenv#installation
2. Install the specific versions of python you wish to test against, generally this would be latest available point
   releases, e.g., `$ pyenv install 3.10.5`. (Obsoleted python versions can be cleaned up with `$ pyenv uninstall <version>`)
3. In root directory of library, create `.python-version` file, and list the versions of python to test against, e.g.:

```text
# .python-version
3.10.5
3.9.13
3.8.13
3.7.13
```

4. Restart shell, run `pyenv local` and the versions listed in `.python-version` should emit to stdout.
5. If an existing poetry environment exists, can remove with `poetry env remove python`.
6. Tell poetry to use the preferred python version specified, e.g., `poetry env use 3.10.5`.
7. Install library and dev dependencies `poetry install --extras "test lint dev"`.

### Existing workflow

If preferred workflow is to interact with `pytest` and `pre-commit` directly, you can do that as
expected:

- `$ poetry run pytest`
- `$ pre-commit run --all-files`

However, all but the most significant changes should be tested across all supported versions. Doing
this locally saves having to wait for a CI failure to pick up cross-version errors.

### Test against all versions

`$ poetry run tox`

#### force recreate tox environments

`$ poetry run tox -r`

#### run specific tox environment

`$ poetry run tox -e py37`

#### run pre-commit only

`$ poetry run -e lint`

---

## Contributing to the documentation

From the squidfunk/mkdocs-material [docker quick start guide](https://hub.docker.com/r/squidfunk/mkdocs-material):

`docker run --rm -it -p 8000:8000 -v ${PWD}:/docs squidfunk/mkdocs-material`

---

## Release workflow

1. Update changelog.md
2. Increment the version in pyproject.toml.
3. Commit and push.
4. In github go to the releases tab
5. Pick "draft a new release"
6. Give it a title and a tag, both vX.X.X
7. Fill in the release description, you can let GitHub do it for you and then edit as needed.
8. Publish the release.
9. look under the action pane and make sure the release action runs correctly
