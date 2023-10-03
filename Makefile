.PHONY: sourcery
sourcery:
	poetry run sourcery review --fix .

.PHONY: docs-clean
docs-clean:
	rm -rf docs/_build

.PHONY: docs-serve
docs-serve:
	sphinx-autobuild docs docs/_build/ -j auto --watch litestar,examples

.PHONY: docs
docs: docs-clean
	sphinx-build -M html docs docs/_build/ -a -j auto -W --keep-going

.PHONY: docs-linkcheck
docs-linkcheck:
	sphinx-build -b linkcheck ./docs ./docs/_build -D linkcheck_ignore='http://.*','https://.*'

.PHONY: docs-linkcheck-full
docs-linkcheck-full:
	sphinx-build -b linkcheck ./docs ./docs/_build -D linkcheck_anchors=0

.PHONY: test-examples
test-examples:
	pytest tests/examples

.PHONY: tests
test:
	pytest tests -n auto

.PHONY: test-all
test-all:
	pytest -m="" -n auto

.PHONY: coverage
coverage:
	pytest tests --cov=litestar -n auto
	coverage html
