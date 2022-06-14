# Contributing

To contribute code changes or update the documentation, please follow these steps:

1. Fork the upstream repository and clone the fork locally.
2. Install [poetry](https://python-poetry.org/), and install the project's dependencies with `poetry install`
3. Install [pre-commit](https://pre-commit.com/) and install the hook by running `pre-commit install`
4. Make whatever changes and additions you wish and commit these - please try to keep your commit history clean.
5. Create a pull request to the main repository with an explanation of your changes

Note: if you add new code or modify existing code - 100% test coverage is mandatory and tests should be well written.

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
