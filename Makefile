.PHONY: docs docs-lint

docs-clean:
	rm -rf docs/_build

docs-serve:
	sphinx-autobuild docs docs/_build/ -j auto --watch starlite,examples

docs: docs-clean
	sphinx-build -M html docs docs/_build/ -E -a -j auto --keep-going

test-examples:
	pytest docs/examples

test:
	pytest tests

test-all: test test-examples
