# AegisFlow — Real-Time Fraud & AML Detection Platform

AegisFlow is an agentic fraud and anti-money-laundering platform. Transactions enter over a REST gateway, flow through a Kafka pipeline, are scored by a hybrid rules + ML engine, and surface as investigator-ready cases.

## Problem Statement

Card and wire fraud must be judged in under 200 ms, but AML typologies (structuring, layering, rapid movement) only become visible across a window of transactions. A single synchronous model call cannot do both.

AegisFlow splits the problem across cooperating agents on a shared event bus: fast deterministic rules inline, heavier behavioural scoring asynchronously, and case management as the system of record.

## Quick Start

```bash
cp .env.example .env
make up          # start the full infrastructure stack
make db-init     # apply schema (auto-applied on first boot)
make seed        # load reference + demo data
make verify      # M1 acceptance checks
