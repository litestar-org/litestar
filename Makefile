.PHONY: docs

docs-clean:
	rm -rf docs/_build

docs-serve:
	sphinx-autobuild docs docs/_build/ -j auto --watch litestar,examples

docs: docs-clean
	sphinx-build -M html docs docs/_build/ -a -j auto -W --keep-going

docs-test:
	rm -rf test_docs/_build
	sphinx-build -M html test_docs test_docs/_build/ -a

test-examples:
	pytest docs/examples

test-sqlalchemy-asyncpg:
	pytest tests -m='sqlalchemy_asyncpg'

test-sqlalchemy-asyncmy:
	pytest tests -m='sqlalchemy_asyncmy'

test:
	pytest tests -m='not sqlalchemy_asyncmy and not sqlalchemy_asyncpg'

test-all: test test-sqlalchemy-asyncpg test-sqlalchemy-asyncmy test-examples

coverage:
	pytest tests --cov=litestar
	coverage html
