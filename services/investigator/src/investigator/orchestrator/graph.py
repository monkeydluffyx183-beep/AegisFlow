from __future__ import annotations

from collections.abc import Callable

from .state import CaseState

SPECIALISTS = ("link_analyst", "pattern_analyst", "media_researcher", "narrative_writer", "qa_reviewer")


def run_graph(state: CaseState, handlers: dict[str, Callable[[CaseState], CaseState]], max_turns: int = 12) -> CaseState:
    """Minimal LangGraph-compatible supervisor loop with bounded turns and resumable state."""
    for specialist in SPECIALISTS:
        if state.turns >= max_turns:
            state.qa_notes.append("Supervisor stopped at max_turns; human review required.")
            break
        handler = handlers.get(specialist)
        if not handler:
            state.qa_notes.append(f"{specialist} unavailable; narrative must disclose the gap.")
            continue
        state = handler(state)
        state.turns += 1
    return state
