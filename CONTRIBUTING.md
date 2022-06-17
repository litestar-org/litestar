# Contributing

To contribute code changes or update the documentation, please follow these steps:

1. Fork the upstream repository and clone the fork locally.
2. Install [poetry](https://python-poetry.org/), and install the project's dependencies with `poetry install`
3. Install [pre-commit](https://pre-commit.com/) and install the hook by running `pre-commit install`
4. Make whatever changes and additions you wish and commit these - please try to keep your commit history clean.
5. Create a pull request to the main repository with an explanation of your changes

Note: if you add new code or modify existing code - 100% test coverage is mandatory and tests should be well written.

## Tox for testing against different versions

### Config

1. Install and configure [pyenv](https://github.com/pyenv/pyenv)
2. Install required python versions via pyenv, e.g., `$ pyenv install 3.x.x` for each required version.
3. In root directory of library, create .python-version file in root, e.g.:

```text
3.10.5
3.9.13
3.8.13
3.7.13
```

4. Restart shell or run command like: `$ pyenv shell 3.10.5 3.9.13 3.8.13 3.7.13`
5. Remove any existing poetry environment: `$ poetry env remove python`
6. Tell poetry to use system python <sup>1</sup>: `$ poetry env use system`
7. `$ poetry install`

1: Not sure if this is the "right" way to handle this yet, however this prevents poetry from reusing
the local environment in each of the tox environments.

### Run

`$ poetry run tox`

#### force recreate tox environments

`$ poetry run tox -r`

#### run specific tox environment

`$ poetry run tox -e py37`

#### run pre-commit only

`$ poetry run -e lint`

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
