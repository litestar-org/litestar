.PHONY: docs

clean-docs:
	rm -rf docs/_build

docs: clean-docs
	sphinx-build -M html docs docs/_build/ -W -E -a -j auto --keep-going

serve-docs:
	sphinx-autobuild docs docs/_build/ -a -j auto --watch starlite,examples
