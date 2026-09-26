"""Optional live PostgreSQL/PostGIS integration test."""

import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_postgis_extension_is_available_in_configured_test_database() -> None:
    database_url = os.getenv("URBANSENSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set URBANSENSE_TEST_DATABASE_URL to run the live database integration test")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        extension = connection.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
        ).scalar_one_or_none()

    assert extension == "postgis"
