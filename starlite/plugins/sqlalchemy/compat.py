"""SQLAlchemy 1.4/2.0 compatibility layer."""

import sqlalchemy

if sqlalchemy.__version__.startswith("1"):
    SQLALCHEMY_2_INSTALLED = False
else:
    SQLALCHEMY_2_INSTALLED = True
