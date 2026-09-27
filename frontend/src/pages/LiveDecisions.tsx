import type { DecisionRow } from '../api/client'

export function LiveDecisions({ decisions }: { decisions: DecisionRow[] }) {
  return <section aria-label="Live decisions"><strong>{decisions.length}</strong> decisions in the current stream.</section>
}
