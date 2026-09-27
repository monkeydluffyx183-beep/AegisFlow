export type Decision = 'approve' | 'review' | 'decline'

export type ReasonCode = {
  code: string
  label: string
  contribution: number
  direction?: string
}

export type DecisionRow = {
  id: string
  transaction_id: string
  ts: string
  account_id: string
  amount: number
  currency: string
  channel: string
  decision: Decision
  score: number
  latency_ms: number
  reason_codes: ReasonCode[]
  rule_hits: Array<{ rule_id: string; label: string; severity: string; action: string; detail: string }>
  model_version?: string
  degraded?: boolean
}

export type CaseSummary = {
  id: string
  title: string
  priority: number
  status: string
  assigned_to: string | null
  assignee_name: string | null
  sla_due: string
  disposition: string | null
  typology: string
  account_ids: string[]
  created_at: string
  updated_at?: string | null
  alert_count: number
  evidence_count: number
  risk_score: number
}

export type Evidence = {
  id: string
  kind: 'graph' | 'timeline' | 'typology' | 'media' | 'note'
  title: string
  payload: Record<string, any>
  source_ref: Record<string, any>
  created_by: string
  created_at: string
}

export type CaseDetail = CaseSummary & {
  alerts: Array<Record<string, any>>
  evidence: Evidence[]
  drafts: Array<{ id: string; version: number; narrative_md: string; citations: Array<Record<string, any>>; status: string; author: string; reviewed_by?: string; review_rationale?: string }>
  graph: { nodes: Array<Record<string, any>>; edges: Array<Record<string, any>> }
  audit: Array<Record<string, any>>
}

export type Overview = {
  kpis: { transactions_today: number; review_rate: number; open_cases: number; sla_at_risk: number; avg_latency_ms: number; feature_hit_rate: number }
  decision_mix: { approve: number; review: number; decline: number }
  live: DecisionRow[]
  activity: Array<Record<string, any>>
  role: string
}

const mockCases: CaseSummary[] = [
  { id: 'case_ring_1042', title: 'Coordinated smurfing · shared device cluster', priority: 96.4, status: 'pending_review', assigned_to: 'usr_priya', assignee_name: 'Priya Nair', sla_due: '2026-09-27T07:18:00Z', disposition: null, typology: 'smurfing', account_ids: ['acct-ring-1042', 'acct-ring-2281', 'acct-ring-3988', 'acct-ring-4406'], created_at: '2026-09-26T22:44:00Z', alert_count: 14, evidence_count: 4, risk_score: .97 },
  { id: 'case_wire_9071', title: 'High-value transfer · beneficiary mismatch', priority: 71.8, status: 'open', assigned_to: null, assignee_name: null, sla_due: '2026-09-27T11:42:00Z', disposition: null, typology: 'layering', account_ids: ['acct-9071', 'acct-7312'], created_at: '2026-09-27T01:11:00Z', alert_count: 3, evidence_count: 0, risk_score: .81 },
  { id: 'case_review_7312', title: 'Device sharing · elevated velocity', priority: 54.1, status: 'investigating', assigned_to: 'usr_fraud', assignee_name: 'Sofia Chen', sla_due: '2026-09-27T15:00:00Z', disposition: null, typology: 'network_anomaly', account_ids: ['acct-7312'], created_at: '2026-09-27T02:22:00Z', alert_count: 2, evidence_count: 0, risk_score: .64 },
]

const mockReasons = (kind: Decision): ReasonCode[] => kind === 'decline'
  ? [{ code: 'GRAPH_RISK', label: 'Proximity to a known-risk network', contribution: .88 }, { code: 'VELOCITY_1H', label: 'One-hour payment velocity', contribution: .76 }, { code: 'DEVICE_SHARING_DEGREE', label: 'Device shared across accounts', contribution: .68 }]
  : kind === 'review'
    ? [{ code: 'AMOUNT_ZSCORE', label: 'Amount above account baseline', contribution: .61 }, { code: 'NEW_DEVICE', label: 'New device for this account', contribution: .42 }]
    : [{ code: 'ACCOUNT_HISTORY', label: 'Stable account history', contribution: .09, direction: 'decreases_risk' }]

const mockDecisions: DecisionRow[] = Array.from({ length: 12 }, (_, index) => {
  const kind: Decision = index < 4 ? 'decline' : index < 7 ? 'review' : 'approve'
  return { id: `dec-live-${index}`, transaction_id: `tx-live-${index}`, ts: new Date(Date.now() - index * 87_000).toISOString(), account_id: index < 4 ? `acct-ring-${1042 + index * 639}` : `acct-${9071 + index}`, amount: index < 4 ? 720 + index * 138 : 45 + index * 97, currency: 'USD', channel: index % 3 === 0 ? 'transfer' : 'card', decision: kind, score: kind === 'decline' ? .82 + index / 100 : kind === 'review' ? .52 + index / 100 : .08 + index / 100, latency_ms: 2.1 + (index % 4) * .7, reason_codes: mockReasons(kind), rule_hits: kind === 'decline' ? [{ rule_id: 'NET-007', label: 'Known-risk network proximity', severity: 'high', action: 'review', detail: 'Account is close to a known-fraud component' }] : [], model_version: 'fraud-champion-2026.09' }
})

const mockDetail: CaseDetail = {
  ...mockCases[0],
  alerts: mockDecisions.slice(0, 4).map((item, index) => ({ id: `alert-${index}`, transaction_id: item.transaction_id, ts: item.ts, account_id: item.account_id, amount: item.amount, currency: 'USD', channel: item.channel, decision: item.decision, reason: 'Smurfing pattern member', severity: 'critical' })),
  evidence: [
    { id: 'ev_graph_01', kind: 'graph', title: 'Entity network and ring proximity', payload: { nodes: [{ id: 'acct-ring-1042', label: 'A. K. Holdings', type: 'account', risk: 'critical' }, { id: 'acct-ring-2281', label: 'Northstar Trading', type: 'account', risk: 'high' }, { id: 'acct-ring-3988', label: 'Mosaic Services', type: 'account', risk: 'high' }, { id: 'dev-shared-77', label: 'Shared fingerprint 77', type: 'device', risk: 'critical' }, { id: 'ip-198', label: '198.51.100.8', type: 'ip', risk: 'elevated' }], edges: [{ source: 'acct-ring-1042', target: 'dev-shared-77', type: 'uses_device' }, { source: 'acct-ring-2281', target: 'dev-shared-77', type: 'uses_device' }, { source: 'acct-ring-3988', target: 'dev-shared-77', type: 'uses_device' }, { source: 'acct-ring-1042', target: 'ip-198', type: 'uses_ip' }] }, source_ref: { tool: 'khop_neighborhood', case_id: 'case_ring_1042' }, created_by: 'agent', created_at: '2026-09-27T03:02:00Z' },
    { id: 'ev_timeline_01', kind: 'timeline', title: 'Transaction timeline', payload: { count: 14, total_amount: 14355.5, transactions: mockDecisions.slice(0, 4).map((item) => ({ transaction_id: item.transaction_id, ts: item.ts, account_id: item.account_id, amount: item.amount, currency: 'USD', channel: item.channel })) }, source_ref: { tool: 'txn_timeline' }, created_by: 'agent', created_at: '2026-09-27T03:02:00Z' },
    { id: 'ev_typology_01', kind: 'typology', title: 'Smurfing pattern match', payload: { typology: 'smurfing', confidence: .91, supporting_transaction_ids: mockDecisions.slice(0, 4).map((item) => item.transaction_id), finding: 'Fourteen linked, sub-threshold movements in a compact window.' }, source_ref: { tool: 'typology_scan' }, created_by: 'agent', created_at: '2026-09-27T03:02:00Z' },
    { id: 'ev_media_01', kind: 'media', title: 'Adverse-media search', payload: { matches: [{ article_id: 'media-demo-042', source: 'Synthetic Compliance Wire', date: '2026-08-14', excerpt: 'A synthetic adverse-media record references a payment network using shared devices to move funds through layered beneficiaries.', relevance: .86 }] }, source_ref: { tool: 'hybrid_media_search', corpus_version: 'synthetic-news-2026.09' }, created_by: 'agent', created_at: '2026-09-27T03:02:00Z' },
  ],
  drafts: [{ id: 'sar_demo_01', version: 1, status: 'draft', author: 'agent', narrative_md: '## Suspicious Activity Report — Draft\n\n### Subject and activity\nAegisFlow identified a connected activity cluster involving **acct-ring-1042, acct-ring-2281, acct-ring-3988, acct-ring-4406**. The linked activity occurred between **2026-09-26** and **2026-09-27** and totals approximately **14,355.50 USD** across **14 transactions**. [Evidence: ev_timeline_01]\n\n### Why the activity is suspicious\nThe entity graph shows shared infrastructure across the subjects, which is inconsistent with the observed baseline for independent customers. [Evidence: ev_graph_01] The transaction sequence matches a **smurfing** pattern with a model confidence of **91%**. [Evidence: ev_typology_01]\n\n### External context\nA synthetic adverse-media search returned one relevant excerpt mentioning layered movement through shared devices. The excerpt is contextual information and is not treated as proof of wrongdoing. [Evidence: ev_media_01]\n\n### QA status\nAll material claims are linked to evidence items. Human approval is required before export.', citations: [{ evidence_id: 'ev_graph_01' }, { evidence_id: 'ev_timeline_01' }, { evidence_id: 'ev_typology_01' }, { evidence_id: 'ev_media_01' }] }],
  graph: { nodes: [], edges: [] },
  audit: [{ id: 'audit-1', action: 'investigation.completed', actor_id: 'investigator', actor_role: 'agent', created_at: '2026-09-27T03:02:15Z', detail: { evidence_count: 4 } }, { id: 'audit-2', action: 'alert.created', actor_id: 'system', actor_role: 'admin', created_at: '2026-09-27T02:44:00Z', detail: { decision: 'decline' } }],
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) } })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || `Request failed: ${response.status}`)
  return response.json() as Promise<T>
}

export async function getOverview(): Promise<Overview> {
  try { return await request<Overview>('/api/v1/overview') }
  catch { return { kpis: { transactions_today: 1248, review_rate: 2.8, open_cases: 18, sla_at_risk: 3, avg_latency_ms: 3.8, feature_hit_rate: 99.7 }, decision_mix: { approve: 1173, review: 46, decline: 29 }, live: mockDecisions, activity: [], role: 'aml_analyst' } }
}

export async function getDecisions(): Promise<DecisionRow[]> {
  try { return (await request<{ items: DecisionRow[] }>('/api/v1/decisions?limit=50')).items }
  catch { return mockDecisions }
}

export async function getCases(): Promise<CaseSummary[]> {
  try { return (await request<{ items: CaseSummary[] }>('/api/v1/cases?sort=sla')).items }
  catch { return mockCases }
}

export async function getCase(id: string): Promise<CaseDetail> {
  try { return await request<CaseDetail>(`/api/v1/cases/${id}`) }
  catch { return { ...mockDetail, id } }
}

export async function investigateCase(id: string): Promise<any> {
  return request(`/api/v1/cases/${id}/investigate`, { method: 'POST', body: '{}' })
}

export async function saveDraft(id: string, narrative_md: string, citations: Array<Record<string, any>>): Promise<any> {
  try { return await request(`/api/v1/sar/${id}/draft`, { method: 'PUT', body: JSON.stringify({ narrative_md, citations }) }) }
  catch { return { status: 'edited', version: 2 } }
}

export async function approveDraft(id: string, rationale: string): Promise<any> {
  return request(`/api/v1/sar/${id}/approve`, { method: 'POST', headers: { 'X-User-Email': 'marcus@aegisflow.demo', 'X-Role': 'manager' }, body: JSON.stringify({ rationale }) })
}

export async function getModels(): Promise<any> {
  try { return await request('/api/v1/models') }
  catch {
    return { champion: { name: 'fraud-champion', version: 'fraud-champion-2026.09', stage: 'Production', calibration: 'isotonic', features: 12, deployed_at: '2026-09-22T08:00:00Z' }, challenger: { name: 'fraud-challenger-graph', version: 'fraud-challenger-graph-v2', stage: 'Shadow', disagreement_rate: .084, scored: 18420, lift_estimate: '+8.4%' }, promotion_policy: { minimum_lift: .05, minimum_window: 10000, human_approval: true } }
  }
}

export async function getDrift(): Promise<any> {
  try { return await request('/api/v1/drift') }
  catch {
    return { status: 'healthy', features: [{ name: 'velocity_1h', psi: .06, status: 'healthy' }, { name: 'amount_zscore', psi: .11, status: 'healthy' }, { name: 'graph_risk', psi: .17, status: 'watch' }, { name: 'device_sharing_degree', psi: .04, status: 'healthy' }], score_distribution: { psi: .08, status: 'healthy' }, label_delay_days: 2.4 }
  }
}

export async function updateThresholds(review_t: number, decline_t: number): Promise<any> {
  return request('/api/v1/thresholds', { method: 'PUT', headers: { 'X-User-Email': 'marcus@aegisflow.demo', 'X-Role': 'manager' }, body: JSON.stringify({ review_t, decline_t }) })
}

export { mockCases, mockDetail, mockDecisions }
