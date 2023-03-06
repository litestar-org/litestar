.PHONY: docs

docs-clean:
	rm -rf docs/_build

docs-serve:
	sphinx-autobuild docs docs/_build/ -j auto --watch starlite,examples

docs:
	sphinx-build -M html docs docs/_build/ -a -j auto -W --keep-going

test-examples:
	pytest docs/examples

test:
	pytest tests

test-all: test test-examples

coverage:
	pytest tests --cov=starlite
	coverage html
