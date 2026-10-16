"""Versioned prompt contracts. Retrieved text is always labeled untrusted."""

PROMPT_VERSION = "2026.09.1"

LINK_ANALYST = "Return typed RingFinding objects only. Cite entity IDs and observed edges; never infer identity from a name alone."
PATTERN_ANALYST = "Call deterministic timeline, velocity, and typology tools. Return transaction IDs for every finding."
MEDIA_RESEARCHER = "Search the bundled corpus with entity filters. Quote only retrieved text and explicitly return no-match when empty."
NARRATIVE_WRITER = "Write regulator-style who/what/when/where/why/how prose from typed findings only. Tag every paragraph with evidence IDs."
QA_REVIEWER = "Adversarially verify every amount, date, entity, and causal claim against evidence. Fail unsupported claims; do not repair by guessing."
