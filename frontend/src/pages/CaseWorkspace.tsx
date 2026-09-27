import type { CaseDetail } from '../api/client'

export function CaseWorkspace({ detail }: { detail: CaseDetail }) {
  return <section aria-label="Case workspace"><h2>{detail.title}</h2><span>{detail.evidence.length} evidence items</span></section>
}
