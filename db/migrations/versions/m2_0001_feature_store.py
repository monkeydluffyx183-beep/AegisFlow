"""M2 feature-store support: unique edges, graph snapshots, known fraud.

Revision ID: m2_0001
Revises: None (the original M1 repository used SQLAlchemy create_all/SQL files)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m2_0001"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    edge_columns = _columns("entity_edges")
    if "src_type" not in edge_columns:
        op.add_column("entity_edges", sa.Column("src_type", sa.String(16), nullable=True, server_default="account"))
    if "dst_type" not in edge_columns:
        op.add_column("entity_edges", sa.Column("dst_type", sa.String(16), nullable=True, server_default="account"))
    bind.execute(sa.text("UPDATE entity_edges SET src_type = COALESCE(src_type, 'account'), dst_type = COALESCE(dst_type, CASE WHEN edge_type = 'uses_device' THEN 'device' WHEN edge_type = 'uses_ip' THEN 'ip' WHEN edge_type = 'pays_merchant' THEN 'merchant' ELSE 'account' END)"))
    # A retry from M1 may have made duplicate edges. Consolidate before enforcing D6.
    bind.execute(sa.text("""
        WITH grouped AS (
            SELECT min(id) AS keep_id, sum(weight) AS total_weight, min(first_seen) AS first_seen,
                   src_type, src_id, dst_type, dst_id, edge_type
            FROM entity_edges
            GROUP BY src_type, src_id, dst_type, dst_id, edge_type
        )
        UPDATE entity_edges AS edge
        SET weight = grouped.total_weight, first_seen = grouped.first_seen
        FROM grouped
        WHERE edge.id = grouped.keep_id
    """))
    bind.execute(sa.text("""
        DELETE FROM entity_edges
        WHERE id NOT IN (
            SELECT min(id) FROM entity_edges
            GROUP BY src_type, src_id, dst_type, dst_id, edge_type
        )
    """))
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("entity_edges")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("entity_edges")}
    if "uq_entity_edges_key" not in indexes and "uq_entity_edges_key" not in constraints:
        op.create_index("uq_entity_edges_key", "entity_edges", ["src_type", "src_id", "dst_type", "dst_id", "edge_type"], unique=True)

    tables = {table for table in sa.inspect(bind).get_table_names()}
    if "graph_feature_snapshots" not in tables:
        op.create_table(
            "graph_feature_snapshots",
            sa.Column("entity_id", sa.String(96), nullable=False),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("component_size", sa.Integer(), nullable=False),
            sa.Column("dist_to_fraud", sa.Integer(), nullable=False),
            sa.Column("risk_rank", sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint("entity_id", "computed_at", name="pk_graph_feature_snapshots"),
        )
        op.create_index("ix_graph_snapshots_time", "graph_feature_snapshots", ["computed_at"])
    if "known_fraud_entities" not in tables:
        op.create_table(
            "known_fraud_entities",
            sa.Column("entity_type", sa.String(16), nullable=False),
            sa.Column("entity_id", sa.String(96), nullable=False),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(32), nullable=False),
            sa.PrimaryKeyConstraint("entity_type", "entity_id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = {table for table in sa.inspect(bind).get_table_names()}
    if "known_fraud_entities" in tables:
        op.drop_table("known_fraud_entities")
    if "graph_feature_snapshots" in tables:
        if "ix_graph_snapshots_time" in {index["name"] for index in sa.inspect(bind).get_indexes("graph_feature_snapshots")}:
            op.drop_index("ix_graph_snapshots_time", table_name="graph_feature_snapshots")
        op.drop_table("graph_feature_snapshots")
    if "uq_entity_edges_key" in {index["name"] for index in sa.inspect(bind).get_indexes("entity_edges")}:
        op.drop_index("uq_entity_edges_key", table_name="entity_edges")
    columns = _columns("entity_edges")
    if "src_type" in columns:
        op.drop_column("entity_edges", "src_type")
    if "dst_type" in columns:
        op.drop_column("entity_edges", "dst_type")
