# Synthetic laundering typologies

The generator includes labeled patterns for evaluation. Labels live in a separate ground-truth sink and are never sent to the scorer.

## Smurfing / structuring

Many accounts or beneficiaries send repeated, relatively small movements in a short window. The generator rotates accounts, shared infrastructure, and amounts below a configurable ceiling. Detectors use count/amount windows and device/IP sharing. The demo case `case_ring_1042` contains fourteen linked movements.

## Layering

Funds move through a chain of accounts or beneficiaries in quick succession, obscuring origin. The generator emits a directed chain with varied amounts and short inter-event times. The pattern tool returns the supporting transaction IDs and does not claim that a chain alone proves criminal intent.

## Round-tripping

Funds return to the source account or its immediate network after several transfers. The generator emits a cycle and slightly changes amounts to model fees or exchange. Graph components and cycle/path features are useful complements to amount and velocity signals.

## Evaluation guidance

- Score event rows without reading `labels`.
- Group alerts by shared entity, device, IP, or ring key.
- Measure typology recall by injected pattern, not by raw alert count.
- Keep synthetic adverse-media text contextual; it is not evidence of real wrongdoing.
