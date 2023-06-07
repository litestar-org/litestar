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

test-sqlalchemy-psycopg-async:
	pytest tests -m='sqlalchemy_psycopg_async'

test-sqlalchemy-psycopg-sync:
	pytest tests -m='sqlalchemy_psycopg_sync'

test-sqlalchemy-asyncmy:
	pytest tests -m='sqlalchemy_asyncmy'

test-sqlalchemy-oracledb:
	pytest tests -m='sqlalchemy_oracledb'

test-sqlalchemy-duckdb:
	pytest tests -m='sqlalchemy_duckdb'

test-sqlalchemy-spanner:
	pytest tests -m='sqlalchemy_spanner'

test-sqlalchemy-integration:
	pytest tests -m='sqlalchemy_integration'

test:
	pytest tests

test-all: test test-sqlalchemy-integration test-examples

coverage:
	pytest tests --cov=litestar
	coverage html
