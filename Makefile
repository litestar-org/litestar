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

.PHONY: test-examples
test-examples:
	pytest tests/examples

.PHONY: test-sqlalchemy-asyncpg
test-sqlalchemy-asyncpg:
	pytest tests -m='sqlalchemy_asyncpg'

.PHONY: test-sqlalchemy-psycopg-async
test-sqlalchemy-psycopg-async:
	pytest tests -m='sqlalchemy_psycopg_async'

.PHONY: test-sqlalchemy-psycopg-sync
test-sqlalchemy-psycopg-sync:
	pytest tests -m='sqlalchemy_psycopg_sync'

.PHONY: test-sqlalchemy-asyncmy
test-sqlalchemy-asyncmy:
	pytest tests -m='sqlalchemy_asyncmy'

.PHONY: test-sqlalchemy-oracledb
test-sqlalchemy-oracledb:
	pytest tests -m='sqlalchemy_oracledb'

.PHONY: test-sqlalchemy-duckdb
test-sqlalchemy-duckdb:
	pytest tests -m='sqlalchemy_duckdb'

.PHONY: test-sqlalchemy-spanner
test-sqlalchemy-spanner:
	pytest tests -m='sqlalchemy_spanner'

.PHONY: test-sqlalchemy-integration
test-sqlalchemy-integration:
	pytest tests -m='sqlalchemy_integration'

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
