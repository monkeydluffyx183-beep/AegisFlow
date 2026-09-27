import type { CaseSummary } from '../api/client'

export function CaseQueue({ cases }: { cases: CaseSummary[] }) {
  return <section aria-label="Case queue"><strong>{cases.length}</strong> cases loaded.</section>
}
