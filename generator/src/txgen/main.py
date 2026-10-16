from __future__ import annotations

import argparse
import json
import random
import time
import urllib.request

from .behavior import normal_transaction
from .fraud_rings import inject_ring
from .labels import write_labels
from .population import build_population
from .typologies import generate_layering, generate_round_tripping, generate_smurfing


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream synthetic AegisFlow transactions")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:8000/api/v1/transactions")
    parser.add_argument("--seed", type=int, default=183)
    parser.add_argument("--replay", type=float, default=0, help="seconds between events; 0 sends as fast as possible")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    accounts, _ = build_population(seed=args.seed)
    account_ids = [account.id for account in accounts[:8]]
    rows = [normal_transaction(accounts[rng.randrange(len(accounts))], rng, idx) for idx in range(max(0, args.count - 32))]
    rows += generate_smurfing(account_ids, 12, args.seed)
    rows += generate_layering(account_ids[:5], 5, args.seed + 1)
    rows += generate_round_tripping(account_ids[:4])
    rows += inject_ring(account_ids[:4], count=11, seed=args.seed)
    write_labels(rows)
    if args.dry_run:
        for row in rows[:args.count]:
            print(json.dumps(row))
        return
    sent = 0
    for row in rows[:args.count]:
        data = json.dumps(row).encode("utf-8")
        request = urllib.request.Request(args.endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                response.read()
            sent += 1
        except Exception as exc:
            print(f"stream stopped after {sent} events: {exc}")
            break
        if args.replay:
            time.sleep(args.replay)
    print(f"generated={len(rows[:args.count])} sent={sent} labels=data/ground_truth.jsonl")


if __name__ == "__main__":
    main()
