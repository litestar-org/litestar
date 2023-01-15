.PHONY: docs

docs-clean:
	rm -rf docs/_build

docs-serve:
	sphinx-autobuild docs docs/_build/ -a -j auto --watch starlite,examples

docs: docs-clean
	sphinx-build -M html docs docs/_build/ -W -E -a -j auto --keep-going
