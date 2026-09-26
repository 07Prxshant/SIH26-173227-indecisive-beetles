"""Tests for PostgreSQL/PostGIS connection configuration."""

from app.core.config import Settings


def test_settings_builds_postgresql_url_from_environment_values() -> None:
    settings = Settings(
        _env_file=None,
        postgres_host="db.local",
        postgres_port=5544,
        postgres_db="urban_test",
        postgres_user="tester",
        postgres_password="secret",
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+psycopg://tester:secret@db.local:5544/urban_test"
    )
