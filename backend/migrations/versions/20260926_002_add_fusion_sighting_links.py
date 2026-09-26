"""Add backend-only links used by the pothole fusion engine.

Revision ID: 20260926_002
Revises: 20260926_001
Create Date: 2026-09-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260926_002"
down_revision = "20260926_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the resolved road segment and the incident a sighting supports."""
    op.add_column("raw_sightings", sa.Column("road_segment_id", sa.String(length=255), nullable=True))
    op.add_column("raw_sightings", sa.Column("incident_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_raw_sightings_incident_id_verified_incidents",
        "raw_sightings",
        "verified_incidents",
        ["incident_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_raw_sightings_road_segment_id", "raw_sightings", ["road_segment_id"])
    op.create_index("ix_raw_sightings_incident_id", "raw_sightings", ["incident_id"])


def downgrade() -> None:
    """Remove fusion-engine metadata without touching persisted incidents."""
    op.drop_index("ix_raw_sightings_incident_id", table_name="raw_sightings")
    op.drop_index("ix_raw_sightings_road_segment_id", table_name="raw_sightings")
    op.drop_constraint("fk_raw_sightings_incident_id_verified_incidents", "raw_sightings", type_="foreignkey")
    op.drop_column("raw_sightings", "incident_id")
    op.drop_column("raw_sightings", "road_segment_id")
