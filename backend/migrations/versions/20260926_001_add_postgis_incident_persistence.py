"""Add PostGIS-backed raw sightings and verified incidents.

Revision ID: 20260926_001
Revises:
Create Date: 2026-09-26
"""

from alembic import op
from geoalchemy2 import Geography, Geometry
import sqlalchemy as sa


revision = "20260926_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable PostGIS and create persistence tables and spatial indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "raw_sightings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.String(length=255), nullable=False),
        sa.Column("class", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("frame_id", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_raw_sightings_event_id", "raw_sightings", ["event_id"])
    op.create_index("ix_raw_sightings_track_id", "raw_sightings", ["track_id"])
    op.create_index("ix_raw_sightings_source_id", "raw_sightings", ["source_id"])
    op.create_index("ix_raw_sightings_location_gist", "raw_sightings", ["location"], postgresql_using="gist")

    op.create_table(
        "verified_incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("geometry", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("road_segment_id", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sighting_count", sa.Integer(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("representative_image", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verified_incidents_road_segment_id", "verified_incidents", ["road_segment_id"])
    op.create_index("ix_verified_incidents_status", "verified_incidents", ["status"])
    op.create_index("ix_verified_incidents_geometry_gist", "verified_incidents", ["geometry"], postgresql_using="gist")


def downgrade() -> None:
    """Remove project tables while retaining the shared PostGIS extension."""
    op.drop_table("verified_incidents")
    op.drop_table("raw_sightings")
