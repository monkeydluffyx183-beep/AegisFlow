"""Seed pre-T0 known fraud only; serving code never reads ground-truth labels.

Usage: DATABASE_URL=postgresql+psycopg://... [KNOWN_FRAUD_CUTOFF=...] \
       python db/seed/seed_known_fraud.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import psycopg

LABEL_SQL = """
SELECT DISTINCT t.account_id, min(t.ts) OVER (PARTITION BY t.account_id) AS confirmed_at
FROM ground_truth_labels AS g
JOIN transactions AS t ON t.id = g.transaction_id
WHERE g.is_fraud AND t.ts < %s
"""
DEFAULT_CUTOFF_SQL = "SELECT percentile_disc(0.10) WITHIN GROUP (ORDER BY ts) FROM transactions"


def main() -> int:
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    dsn = raw_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(dsn) as connection:
        env_cutoff = os.getenv("KNOWN_FRAUD_CUTOFF")
        cutoff = datetime.fromisoformat(env_cutoff[:-1] + "+00:00" if env_cutoff and env_cutoff.endswith("Z") else env_cutoff) if env_cutoff else connection.execute(DEFAULT_CUTOFF_SQL).fetchone()[0]
        if cutoff is None:
            print("no transactions yet - run the generator first", file=sys.stderr)
            return 2
        rows = connection.execute(LABEL_SQL, (cutoff,)).fetchall()
        connection.execute("DELETE FROM known_fraud_entities WHERE source = 'seed_pre_T0'")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO known_fraud_entities (entity_type, entity_id, confirmed_at, source) VALUES ('account', %s, %s, 'seed_pre_T0') ON CONFLICT DO NOTHING",
                rows,
            )
        connection.commit()
    print(f"T0 = {cutoff.isoformat()} -> {len(rows)} known-fraud accounts seeded")
    print("Record T0 in params.yaml as features.known_fraud_cutoff; M3's train split starts here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
