# ADR 0001: single-source online/offline features

- Status: accepted
- Date: 2026-09-27

## Decision

Declare feature metadata once in `ml/src/aegis_ml/features/definitions.py`. The offline builder consumes the definitions in event-time order, and the online reader exposes the same names, windows, and defaults. Redis keys are part of the definition contract; atomic velocity updates use Lua.

## Context

Training-serving skew is a silent failure mode in fraud systems. Duplicating a feature formula in a notebook and in a serving handler makes a model look good in evaluation but behave differently at payment time.

## Consequences

Feature changes require a versioned code review and parity fixture. The definitions module stays deliberately small and dependency-light. A production implementation may compile the same specs to PyArrow and Redis commands, but it cannot add serving-only formulas without a parity test.
