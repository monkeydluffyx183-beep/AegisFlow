from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def prepare(input_dir: str, output: str) -> None:
    """Lightweight contract for IEEE-CIS ETL; parquet writing is optional in the demo image.

    The real job should use point-in-time joins and PyArrow. This fallback writes JSONL with a
    parquet-shaped output path so CI can validate the stage without downloading Kaggle data.
    """
    source = Path(input_dir)
    rows = []
    for csv_path in sorted(source.glob("*.csv")) if source.exists() else []:
        with csv_path.open(newline="", encoding="utf-8", errors="ignore") as handle:
            rows.extend(csv.DictReader(handle))
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(json.dumps(row) for row in rows[:100_000]) + ("\n" if rows else ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/ieee-cis")
    parser.add_argument("--output", default="data/processed/ieee.parquet")
    args = parser.parse_args()
    prepare(args.input, args.output)


if __name__ == "__main__":
    main()
