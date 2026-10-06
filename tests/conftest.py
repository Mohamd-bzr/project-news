"""Shared fixtures for the test suite.

The SQLite file (`.mohmd_news.db`) is runtime state — gitignored, so a CI
checkout (or any fresh clone) starts with NO database. Every table the
schema defines is `CREATE TABLE IF NOT EXISTS`, so initializing it once per
session is safe on a live database and required on a virgin tree.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _database_schema():
    import database

    database.init_db()
