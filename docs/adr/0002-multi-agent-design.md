# ADR 0002: typed specialist investigation graph

- Status: accepted
- Date: 2026-09-27

## Decision

Use a bounded supervisor workflow with link, pattern, adverse-media, narrative, and QA specialists. Deterministic tools compute graph/timeline/typology facts; agents interpret typed outputs. Every draft paragraph carries evidence IDs. A missing specialist returns `FindingUnavailable` rather than invented content.

## Context

A single free-form LLM prompt is difficult to audit and can turn retrieved media into unsupported claims. AML work is evidence assembly plus a human judgment, not autonomous filing.

## Consequences

The local demo can run without an LLM key and produces repeatable golden outputs. A LangGraph adapter can replace the loop later, but must preserve the state schema, maximum twelve turns, retry/timeouts, QA gate, and human approval invariant.
