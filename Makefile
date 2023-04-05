.PHONY: docs

docs-clean:
	rm -rf docs/_build

docs-serve:
	sphinx-autobuild docs docs/_build/ -j auto --watch starlite,examples

docs: docs-clean
	sphinx-build -M html docs docs/_build/ -a -j auto -W --keep-going

docs-test:
	rm -rf test_docs/_build
	sphinx-build -M html test_docs test_docs/_build/ -a

test-examples:
	pytest docs/examples

test:
	pytest tests

test-all: test test-examples

coverage:
	pytest tests --cov=starlite
	coverage html
