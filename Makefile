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

test:
	pytest tests -m='not sqlalchemy_asyncmy and not sqlalchemy_asyncpg and not sqlalchemy_psycopg_async and not sqlalchemy_psycopg_sync and not sqlalchemy_oracledb'

test-all: test test-sqlalchemy-asyncpg test-sqlalchemy-asyncmy test-sqlalchemy_psycopg_async test-sqlalchemy_psycopg_sync test-sqlalchemy_oracledb test-examples

coverage:
	pytest tests --cov=litestar
	coverage html
