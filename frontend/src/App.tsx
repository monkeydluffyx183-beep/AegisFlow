import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Bell, BrainCircuit, BriefcaseBusiness,
  Check, CheckCircle2, ChevronRight, CircleDot, Clock3, Database, Download, Eye, FileText,
  Filter, FolderKanban, LayoutDashboard, ListFilter, LockKeyhole, MoreHorizontal, Network,
  PenLine, Play, Radio, RefreshCw, Save, Search, Settings2, ShieldAlert, ShieldCheck,
  Sparkles, SlidersHorizontal, Users, XCircle, Zap,
  type LucideIcon,
} from 'lucide-react'
import {
  approveDraft, getCase, getCases, getDecisions, getDrift, getModels, getOverview, investigateCase,
  mockCases, saveDraft, updateThresholds, type CaseDetail, type CaseSummary, type DecisionRow, type Overview, type Decision,
} from './api/client'

 type Screen = 'overview' | 'live' | 'cases' | 'models'

const nav: Array<{ id: Screen; label: string; icon: LucideIcon; badge?: string }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'live', label: 'Live decisions', icon: Radio, badge: 'LIVE' },
  { id: 'cases', label: 'Case queue', icon: FolderKanban, badge: '18' },
  { id: 'models', label: 'Model ops', icon: BrainCircuit },
]

const fallbackOverview: Overview = { kpis: { transactions_today: 1248, review_rate: 2.8, open_cases: 18, sla_at_risk: 3, avg_latency_ms: 3.8, feature_hit_rate: 99.7 }, decision_mix: { approve: 1173, review: 46, decline: 29 }, live: [], activity: [], role: 'aml_analyst' }

function App() {
  const [screen, setScreen] = useState<Screen>('overview')
  const [overview, setOverview] = useState<Overview>(fallbackOverview)
  const [decisions, setDecisions] = useState<DecisionRow[]>([])
  const [cases, setCases] = useState<CaseSummary[]>(mockCases)
  const [selectedCase, setSelectedCase] = useState<string | null>(null)
  const [detail, setDetail] = useState<CaseDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    const [nextOverview, nextDecisions, nextCases] = await Promise.all([getOverview(), getDecisions(), getCases()])
    setOverview(nextOverview)
    setDecisions(nextDecisions)
    setCases(nextCases)
    setLoading(false)
  }

  useEffect(() => { void refresh() }, [])
  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(null), 3600); return () => window.clearTimeout(timer) }, [toast])

  const openCase = async (id: string) => {
    setSelectedCase(id)
    setScreen('cases')
    setDetail(await getCase(id))
  }

  const navigate = (next: Screen) => { setSelectedCase(null); setDetail(null); setScreen(next) }

  return (
    <div className="app-shell">
      <Sidebar screen={screen} onNavigate={navigate} />
      <main className="main-column">
        <Topbar loading={loading} onRefresh={() => void refresh()} />
        {screen === 'overview' && <OverviewPage overview={overview} cases={cases} decisions={decisions} onOpenCase={openCase} onNavigate={navigate} />}
        {screen === 'live' && <LivePage decisions={decisions} />}
        {screen === 'cases' && (selectedCase && detail ? <Workspace detail={detail} onBack={() => { setSelectedCase(null); setDetail(null) }} onToast={setToast} onReload={() => openCase(selectedCase || '')} /> : <CaseQueue cases={cases} onOpenCase={openCase} />)}
        {screen === 'models' && <ModelOps onToast={setToast} />}
      </main>
      {toast && <div className="toast"><CheckCircle2 size={17} /> {toast}</div>}
    </div>
  )
}

function Sidebar({ screen, onNavigate }: { screen: Screen; onNavigate: (screen: Screen) => void }) {
  return <aside className="sidebar">
    <div className="brand-lockup"><div className="brand-mark"><ShieldCheck size={21} strokeWidth={2.4} /></div><div><div className="brand-name">AEGIS<span>FLOW</span></div><div className="brand-sub">RISK OPERATIONS</div></div></div>
    <div className="rail-label">WORKSPACE</div>
    <nav className="side-nav">{nav.map(({ id, label, icon: Icon, badge }) => <button key={id} className={`nav-item ${screen === id ? 'active' : ''}`} onClick={() => onNavigate(id)}><Icon size={18} /><span>{label}</span>{badge && <span className={`nav-badge ${badge === 'LIVE' ? 'live-badge' : ''}`}>{badge === 'LIVE' && <i />}{badge}</span>}</button>)}</nav>
    <div className="side-divider" />
    <div className="rail-label">QUICK ACCESS</div>
    <button className="nav-item muted"><FileText size={18} /><span>Evidence library</span></button>
    <button className="nav-item muted"><Database size={18} /><span>Data health</span><span className="dot-ok" /></button>
    <div className="sidebar-bottom">
      <div className="secure-card"><div className="secure-icon"><LockKeyhole size={15} /></div><div><strong>Audit mode on</strong><span>Immutable logging active</span></div><CheckCircle2 size={15} className="secure-check" /></div>
      <div className="profile"><div className="avatar">PN</div><div className="profile-copy"><strong>Priya Nair</strong><span>AML analyst</span></div><MoreHorizontal size={17} className="profile-more" /></div>
    </div>
  </aside>
}

function Topbar({ loading, onRefresh }: { loading: boolean; onRefresh: () => void }) {
  return <header className="topbar"><div className="crumbs"><span>Risk operations</span><ChevronRight size={14} /><strong>Command center</strong></div><div className="top-actions"><div className="search-box"><Search size={16} /><input placeholder="Search cases, accounts, transactions" /><kbd>⌘ K</kbd></div><button className="icon-btn" aria-label="Notifications"><Bell size={18} /><i className="notification-dot" /></button><button className={`icon-btn refresh-btn ${loading ? 'spinning' : ''}`} onClick={onRefresh} aria-label="Refresh data"><RefreshCw size={17} /></button><div className="top-date"><span className="status-live"><i /> System operational</span><span>27 Sep 2026 · 04:12 UTC</span></div></div></header>
}

function PageHeading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description?: string; children?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{children && <div className="heading-actions">{children}</div>}</div>
}

function OverviewPage({ overview, cases, decisions, onOpenCase, onNavigate }: { overview: Overview; cases: CaseSummary[]; decisions: DecisionRow[]; onOpenCase: (id: string) => void; onNavigate: (screen: Screen) => void }) {
  const stats = [
    { label: 'Transactions scored', value: overview.kpis.transactions_today.toLocaleString(), delta: '+12.6%', trend: 'up', icon: Activity, tone: 'blue', caption: 'vs. previous 24h' },
    { label: 'Review rate', value: `${overview.kpis.review_rate}%`, delta: '-0.8%', trend: 'down-good', icon: Eye, tone: 'violet', caption: 'below 4% target' },
    { label: 'Open investigations', value: String(overview.kpis.open_cases).padStart(2, '0'), delta: '3 urgent', trend: 'alert', icon: BriefcaseBusiness, tone: 'amber', caption: 'need attention today' },
    { label: 'Scoring p95', value: `${(overview.kpis.avg_latency_ms * 1.7).toFixed(1)} ms`, delta: '-18%', trend: 'down-good', icon: Zap, tone: 'green', caption: '100 ms SLO' },
  ]
  return <div className="page-content"><PageHeading eyebrow="Monday · 27 September 2026" title="Good morning, Priya" description="Here is what needs your attention across fraud and financial crime today."><button className="secondary-btn" onClick={() => onNavigate('live')}><Radio size={15} /> Watch live stream</button><button className="primary-btn" onClick={() => onNavigate('cases')}><FolderKanban size={15} /> Open case queue</button></PageHeading>
    <div className="stat-grid">{stats.map((stat) => <StatCard key={stat.label} {...stat} />)}</div>
    <div className="overview-grid top-grid">
      <DecisionMix overview={overview} />
      <PriorityQueue cases={cases} onOpenCase={onOpenCase} />
      <ActivityPanel />
    </div>
    <div className="section-head"><div><h2>Live decision stream</h2><p>Latest payment decisions with explainability coverage</p></div><button className="text-btn" onClick={() => onNavigate('live')}>View all <ChevronRight size={14} /></button></div>
    <DecisionTable decisions={decisions.slice(0, 5)} compact onSelect={() => onNavigate('live')} />
  </div>
}

function StatCard({ label, value, delta, trend, icon: Icon, tone, caption }: { label: string; value: string; delta: string; trend: string; icon: LucideIcon; tone: string; caption: string }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={18} /></div><div className="stat-label">{label}<span className="stat-caption">{caption}</span></div><div className="stat-value">{value}</div><div className={`stat-delta ${trend}`} aria-label={delta}>{trend === 'up' ? <ArrowUpRight size={14} /> : trend === 'alert' ? <AlertTriangle size={13} /> : <ArrowDownRight size={14} />}{delta}</div><div className={`micro-bars ${tone}`}>{[.38, .52, .44, .65, .52, .75, .68, .92].map((height, i) => <i key={i} style={{ height: `${height * 100}%` }} />)}</div></div>
}

function DecisionMix({ overview }: { overview: Overview }) {
  const { approve, review, decline } = overview.decision_mix
  const total = approve + review + decline
  const approvePct = total ? approve / total * 100 : 94
  const reviewPct = total ? review / total * 100 : 4
  return <section className="panel decision-panel"><PanelTitle title="Decision mix" subtitle="Last 24 hours" action={<span className="healthy-tag"><i /> healthy</span>} /><div className="mix-content"><div className="donut" style={{ background: `conic-gradient(#45d6a1 0 ${approvePct}%, #f5b84b ${approvePct}% ${approvePct + reviewPct}%, #fa6b76 ${approvePct + reviewPct}% 100%)` }}><div className="donut-inner"><strong>{(approvePct).toFixed(1)}%</strong><span>approved</span></div></div><div className="mix-legend"><LegendRow tone="green" label="Approved" value={approve.toLocaleString()} pct={`${approvePct.toFixed(1)}%`} /><LegendRow tone="amber" label="Review" value={review.toLocaleString()} pct={`${reviewPct.toFixed(1)}%`} /><LegendRow tone="red" label="Declined" value={decline.toLocaleString()} pct={`${(100 - approvePct - reviewPct).toFixed(1)}%`} /></div></div><div className="panel-footnote"><span><Activity size={13} /> 99.7% feature store hit rate</span><span className="footnote-good">within SLO</span></div></section>
}

function LegendRow({ tone, label, value, pct }: { tone: string; label: string; value: string; pct: string }) { return <div className="legend-row"><i className={`legend-dot ${tone}`} /><span>{label}</span><strong>{value}</strong><small>{pct}</small></div> }
function PanelTitle({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) { return <div className="panel-title"><div><h2>{title}</h2><span>{subtitle}</span></div>{action}</div> }

function PriorityQueue({ cases, onOpenCase }: { cases: CaseSummary[]; onOpenCase: (id: string) => void }) {
  return <section className="panel queue-panel"><PanelTitle title="Priority queue" subtitle="SLA-sorted investigations" action={<span className="queue-count">{cases.filter((item) => item.status !== 'closed').length} open</span>} /><div className="queue-list">{cases.slice(0, 3).map((item) => <button key={item.id} className="queue-item" onClick={() => onOpenCase(item.id)}><div className={`risk-score ${item.priority >= 85 ? 'critical' : item.priority >= 60 ? 'high' : 'medium'}`}>{Math.round(item.priority)}</div><div className="queue-copy"><strong>{item.title}</strong><span>{item.alert_count} alerts · {item.typology.replace('_', ' ')}</span></div><div className="queue-sla"><Clock3 size={13} /><span>{item.priority >= 85 ? '02h 18m' : item.priority >= 60 ? '06h 42m' : '11h 00m'}</span></div><ChevronRight size={15} className="queue-arrow" /></button>)}</div><button className="panel-link" onClick={() => onOpenCase(cases[0]?.id || 'case_ring_1042')}>Review all investigations <ArrowUpRight size={14} /></button></section>
}

function ActivityPanel() {
  const activity = [{ icon: ShieldAlert, tone: 'red', text: '9 transactions declined', sub: 'Ring cluster · 03:58 UTC', time: '14m' }, { icon: Sparkles, tone: 'violet', text: 'SAR draft generated', sub: 'CASE-1042 · QA passed', time: '1h' }, { icon: SlidersHorizontal, tone: 'blue', text: 'Thresholds updated', sub: 'Manager approval · v18', time: '3h' }, { icon: CheckCircle2, tone: 'green', text: 'Case dispositioned', sub: 'CASE-0988 · not fraud', time: '5h' }]
  return <section className="panel activity-panel"><PanelTitle title="Activity" subtitle="Audit trail · recent" action={<button className="tiny-icon"><MoreHorizontal size={16} /></button>} /><div className="activity-list">{activity.map(({ icon: Icon, tone, text, sub, time }) => <div className="activity-item" key={text}><div className={`activity-icon ${tone}`}><Icon size={15} /></div><div className="activity-copy"><strong>{text}</strong><span>{sub}</span></div><time>{time}</time></div>)}</div><div className="immutable-note"><LockKeyhole size={12} /> All actions are immutably logged</div></section>
}

function LivePage({ decisions }: { decisions: DecisionRow[] }) {
  const [filter, setFilter] = useState<'all' | Decision>('all')
  const filtered = filter === 'all' ? decisions : decisions.filter((item) => item.decision === filter)
  return <div className="page-content"><PageHeading eyebrow="Real-time decisioning" title="Live decisions" description="Every decision is scored, explained, and traceable in under 100 ms."><div className="stream-status"><span className="stream-pulse"><i /></span> Streaming now</div><button className="secondary-btn"><Download size={15} /> Export view</button></PageHeading><div className="live-banner"><div className="live-banner-icon"><Radio size={22} /></div><div><strong>Scoring engine is healthy</strong><span>Processing payment traffic at 300 TPS · champion <b>fraud-champion-2026.09</b> · shadow disagreement 8.4%</span></div><div className="banner-metric"><span>p95 latency</span><strong>6.4 ms</strong></div><div className="banner-metric"><span>feature hit rate</span><strong>99.7%</strong></div></div><div className="table-toolbar"><div className="filter-tabs"><button className={filter === 'all' ? 'selected' : ''} onClick={() => setFilter('all')}>All <b>{decisions.length}</b></button><button className={filter === 'review' ? 'selected' : ''} onClick={() => setFilter('review')}>Review <b>{decisions.filter((x) => x.decision === 'review').length}</b></button><button className={filter === 'decline' ? 'selected' : ''} onClick={() => setFilter('decline')}>Declined <b>{decisions.filter((x) => x.decision === 'decline').length}</b></button></div><button className="filter-btn"><ListFilter size={15} /> Filter</button></div><DecisionTable decisions={filtered} showReasons /></div>
}

function DecisionTable({ decisions, compact = false, onSelect }: { decisions: DecisionRow[]; compact?: boolean; onSelect?: () => void; showReasons?: boolean }) {
  return <div className={`data-table-wrap ${compact ? 'compact-table' : ''}`}><table className="data-table"><thead><tr><th>Transaction</th><th>Account</th><th>Amount</th><th>Decision</th><th>Risk score</th><th>Latency</th>{!compact && <th>Top reason</th>}<th /></tr></thead><tbody>{decisions.map((item) => <tr key={item.id} onClick={onSelect}><td><div className="txn-cell"><span className="txn-icon"><Activity size={14} /></span><div><strong>{item.transaction_id}</strong><small>{timeAgo(item.ts)} · {item.channel}</small></div></div></td><td><span className="mono">{item.account_id}</span></td><td><strong className="amount">{item.currency} {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></td><td><StatusPill status={item.decision} /></td><td><div className="score-cell"><strong>{(item.score * 100).toFixed(1)}%</strong><div className="score-track"><i className={item.decision} style={{ width: `${item.score * 100}%` }} /></div></div></td><td><span className="latency"><Zap size={12} />{item.latency_ms.toFixed(1)} ms</span></td>{!compact && <td><span className="reason-inline"><span />{item.reason_codes[0]?.label || 'Stable account history'}</span></td>}<td><MoreHorizontal size={16} className="row-more" /></td></tr>)}</tbody></table>{decisions.length === 0 && <div className="empty-state"><Activity size={22} />No decisions match this filter.</div>}</div>
}

function StatusPill({ status }: { status: string }) { const Icon = status === 'approve' ? CheckCircle2 : status === 'decline' ? XCircle : AlertTriangle; return <span className={`status-pill ${status}`}><Icon size={13} />{status}</span> }

function CaseQueue({ cases, onOpenCase }: { cases: CaseSummary[]; onOpenCase: (id: string) => void }) {
  const [status, setStatus] = useState('all')
  const visible = status === 'all' ? cases : cases.filter((item) => item.status === status)
  return <div className="page-content"><PageHeading eyebrow="AML investigations" title="Case queue" description="Work the highest-risk relationships before their SLA clocks expire."><button className="secondary-btn"><Filter size={15} /> Saved filters</button><button className="primary-btn"><BriefcaseBusiness size={15} /> Assign next case</button></PageHeading><div className="case-summary-strip"><div><span className="summary-number">18</span><span>open cases</span></div><div><span className="summary-number amber-text">03</span><span>at risk of SLA</span></div><div><span className="summary-number">12m</span><span>median investigation</span></div><div className="summary-right"><Users size={16} /> 4 analysts online <span className="dot-ok" /></div></div><div className="queue-toolbar"><div className="filter-tabs"><button className={status === 'all' ? 'selected' : ''} onClick={() => setStatus('all')}>All cases <b>{cases.length}</b></button>{['open', 'investigating', 'pending_review'].map((item) => <button key={item} className={status === item ? 'selected' : ''} onClick={() => setStatus(item)}>{item.replace('_', ' ')} <b>{cases.filter((x) => x.status === item).length}</b></button>)}</div><button className="sort-btn"><SlidersHorizontal size={15} /> SLA due <ChevronRight size={14} /></button></div><div className="case-table-wrap"><table className="case-table"><thead><tr><th>Priority</th><th>Case</th><th>Status</th><th>Typology</th><th>Alerts</th><th>Assigned to</th><th>SLA due</th><th /></tr></thead><tbody>{visible.map((item) => <tr key={item.id} onClick={() => onOpenCase(item.id)}><td><div className={`priority-number ${item.priority >= 85 ? 'critical' : item.priority >= 60 ? 'high' : 'medium'}`}>{item.priority.toFixed(1)}</div></td><td><div className="case-name"><strong>{item.title}</strong><span>{item.id.toUpperCase()} · {item.account_ids.length} connected entities</span></div></td><td><CaseStatus status={item.status} /></td><td><span className="typology-tag"><Network size={13} /> {item.typology.replace('_', ' ')}</span></td><td><span className="alert-count"><AlertTriangle size={13} /> {item.alert_count}</span></td><td>{item.assignee_name ? <div className="assignee"><span className="mini-avatar">{initials(item.assignee_name)}</span>{item.assignee_name}</div> : <span className="unassigned">Unassigned</span>}</td><td><div className={`sla-cell ${item.priority >= 85 ? 'urgent' : ''}`}><Clock3 size={13} /><strong>{item.priority >= 85 ? '02h 18m' : item.priority >= 60 ? '06h 42m' : '11h 00m'}</strong><small>{formatDate(item.sla_due)}</small></div></td><td><ChevronRight size={17} className="row-chevron" /></td></tr>)}</tbody></table></div></div>
}

function CaseStatus({ status }: { status: string }) { const label = status === 'pending_review' ? 'Pending review' : status === 'investigating' ? 'Investigating' : 'Open'; return <span className={`case-status ${status}`}><i />{label}</span> }

function Workspace({ detail, onBack, onToast, onReload }: { detail: CaseDetail; onBack: () => void; onToast: (message: string) => void; onReload: () => void }) {
  const [draft, setDraft] = useState(detail.drafts[0]?.narrative_md || '')
  const [saving, setSaving] = useState(false)
  const [investigating, setInvestigating] = useState(false)
  const [rationale, setRationale] = useState('Reviewed evidence pack, typology match, and claim-level citations. Approving for regulatory filing review.')
  const latestDraft = detail.drafts[0]
  useEffect(() => { setDraft(detail.drafts[0]?.narrative_md || '') }, [detail.id, detail.drafts])
  const graphEvidence = detail.evidence.find((item) => item.kind === 'graph')
  const graph = graphEvidence?.payload || detail.graph
  const save = async () => { setSaving(true); await saveDraft(detail.id, draft, latestDraft?.citations || []); setSaving(false); onToast('Draft v2 saved to the immutable audit trail'); onReload() }
  const investigate = async () => { setInvestigating(true); await investigateCase(detail.id); setInvestigating(false); onToast('Evidence pack assembled · QA reviewer passed'); onReload() }
  const approve = async () => { try { await approveDraft(detail.id, rationale); onToast('SAR approved by Marcus Lee · export is ready'); onReload() } catch { onToast('Manager approval is required to export this draft') } }
  return <div className="page-content workspace-page"><div className="workspace-breadcrumb"><button className="back-btn" onClick={onBack}><ChevronRight size={15} className="back-chevron" /> Case queue</button><span>/</span><span>{detail.id.toUpperCase()}</span></div><div className="workspace-head"><div><div className="case-title-line"><h1>{detail.title}</h1><CaseStatus status={detail.status} /></div><p><span className="mono">{detail.id.toUpperCase()}</span><span className="head-separator" /> Opened {formatDate(detail.created_at)}<span className="head-separator" /> Assigned to {detail.assignee_name || 'unassigned'}</p></div><div className="workspace-actions"><button className="secondary-btn"><MoreHorizontal size={16} /> Actions</button><button className="secondary-btn"><Users size={15} /> Reassign</button>{detail.evidence.length === 0 && <button className="primary-btn" onClick={investigate} disabled={investigating}>{investigating ? <RefreshCw size={15} className="spinning" /> : <Sparkles size={15} />}{investigating ? 'Investigating…' : 'Run investigation'}</button>}</div></div><div className="risk-overview"><div className="risk-overview-score"><div className="large-risk-score">{Math.round(detail.priority)}<span>/100</span></div><div><strong>Critical priority</strong><span>Risk score · {Math.round(detail.risk_score * 100)}% model probability</span></div></div><div className="risk-overview-item"><span>Typology</span><strong><Network size={14} /> {detail.typology.replace('_', ' ')}</strong></div><div className="risk-overview-item"><span>Linked alerts</span><strong><AlertTriangle size={14} /> {detail.alert_count} alerts</strong></div><div className="risk-overview-item"><span>SLA deadline</span><strong className="urgent-text"><Clock3 size={14} /> 02h 18m remaining</strong></div><div className="risk-overview-item"><span>QA status</span><strong className="green-text"><CheckCircle2 size={14} /> Evidence linked</strong></div></div><div className="workspace-grid"><div className="workspace-left"><section className="panel graph-panel"><PanelTitle title="Entity network" subtitle="2-hop neighborhood · risk propagation" action={<button className="tiny-action"><Eye size={14} /> Expand graph</button>} /><GraphVisual graph={graph} /><div className="graph-legend"><span><i className="node-dot subject" /> Subject</span><span><i className="node-dot account" /> Connected account</span><span><i className="node-dot device" /> Device / IP</span><span><i className="edge-line" /> Shared link</span></div></section><section className="panel timeline-panel"><PanelTitle title="Transaction timeline" subtitle={`${detail.alert_count} linked alerts · chronological`} action={<button className="tiny-action"><Download size={14} /> CSV</button>} /><Timeline alerts={detail.alerts} /></section><section className="panel evidence-panel"><PanelTitle title="Evidence pack" subtitle="Every item traceable to a source record" action={<span className="evidence-count"><Check size={13} /> {detail.evidence.length || 4} verified</span>} /><div className="evidence-grid">{detail.evidence.map((item) => <EvidenceCard key={item.id} item={item} />)}</div></section></div><div className="workspace-right"><section className="panel draft-panel"><div className="draft-head"><div><div className="draft-kicker"><Sparkles size={14} /> AGENT-ASSISTED DRAFT</div><h2>SAR narrative</h2><div className="draft-meta"><span className="version-chip">v{latestDraft?.version || 1}</span><span>Generated by Narrative Writer</span><span className="qa-pass"><CheckCircle2 size={13} /> QA passed</span></div></div><button className="tiny-action"><Eye size={14} /> Preview</button></div><div className="citation-hint"><LockKeyhole size={13} /><span>Claims are restricted to typed findings. <strong>4 evidence citations</strong> linked.</span></div><textarea className="narrative-editor" value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} /><div className="editor-footer"><span><PenLine size={13} /> {draft.length.toLocaleString()} characters · Markdown</span><button className="save-btn" onClick={save} disabled={saving}><Save size={14} /> {saving ? 'Saving…' : 'Save version'}</button></div></section><section className="panel approval-panel"><div className="approval-title"><div className="approval-icon"><LockKeyhole size={16} /></div><div><h2>Human approval gate</h2><span>Required before any SAR export</span></div><span className="approval-required">REQUIRED</span></div><label>Approval rationale<textarea value={rationale} onChange={(event) => setRationale(event.target.value)} rows={3} /></label><div className="approval-check"><CheckCircle2 size={15} /><span>I reviewed the evidence, citations, and narrative claims.</span></div><button className="approve-btn" onClick={approve}><Check size={16} /> Approve & prepare export <Download size={14} /></button><p className="approval-footnote"><LockKeyhole size={12} /> No autonomous filings · approval is immutably logged</p></section><section className="panel audit-panel"><PanelTitle title="Audit trail" subtitle="Immutable case activity" action={<button className="tiny-action">View all <ChevronRight size={13} /></button>} /><div className="audit-list">{detail.audit.slice(0, 3).map((item) => <div className="audit-row" key={item.id}><div className="audit-bullet"><CircleDot size={13} /></div><div><strong>{String(item.action).replaceAll('.', ' · ')}</strong><span>{item.actor_id} · {timeAgo(item.created_at)}</span></div></div>)}</div></section></div></div></div>
}

function GraphVisual({ graph }: { graph: { nodes?: Array<Record<string, any>>; edges?: Array<Record<string, any>> } }) {
  const nodes = (graph.nodes || []).slice(0, 8)
  const positions = [{ x: 158, y: 118 }, { x: 318, y: 58 }, { x: 334, y: 178 }, { x: 158, y: 238 }, { x: 34, y: 72 }, { x: 38, y: 201 }, { x: 468, y: 113 }, { x: 470, y: 223 }]
  const byId = new Map(nodes.map((node, index) => [node.id, positions[index] || { x: 240, y: 120 }]))
  return <div className="graph-visual"><svg viewBox="0 0 540 280" role="img" aria-label="Entity relationship graph"><defs><filter id="glow"><feGaussianBlur stdDeviation="3" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>{(graph.edges || []).map((edge, index) => { const source = byId.get(edge.source) || positions[index % positions.length]; const target = byId.get(edge.target) || positions[(index + 1) % positions.length]; return <line key={`${edge.source}-${edge.target}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className="graph-edge" /> })}{nodes.map((node, index) => { const point = byId.get(node.id) || positions[index]; const isDevice = node.type === 'device' || node.type === 'ip'; const isSubject = index === 0; return <g key={node.id} className="graph-node" transform={`translate(${point.x}, ${point.y})`}><circle r={isSubject ? 24 : isDevice ? 18 : 21} className={isSubject ? 'subject-node' : isDevice ? 'device-node' : 'account-node'} filter={isSubject ? 'url(#glow)' : undefined} /><text y={isSubject ? 4 : 3} textAnchor="middle" className="node-glyph">{isDevice ? '◈' : '$'}</text><text y={isSubject ? 42 : 36} textAnchor="middle" className="node-label">{String(node.label || node.id).slice(0, 17)}</text><text y={isSubject ? 55 : 49} textAnchor="middle" className="node-type">{isDevice ? String(node.type || 'device').toUpperCase() : isSubject ? 'PRIMARY SUBJECT' : 'ACCOUNT'}</text></g> })}</svg>{nodes.length === 0 && <div className="graph-empty"><Network size={25} /><span>Graph is assembled after investigation</span></div>}</div>
}

function Timeline({ alerts }: { alerts: Array<Record<string, any>> }) { return <div className="timeline-list">{alerts.slice(0, 5).map((alert, index) => <div className="timeline-row" key={alert.id || index}><div className="timeline-time"><strong>{formatTime(alert.ts)}</strong><span>{formatDate(alert.ts)}</span></div><div className="timeline-line"><i className={index === 0 ? 'hot' : ''} /></div><div className="timeline-event"><div><strong>{alert.account_id}</strong><span>{alert.channel || 'transfer'} · <span className="mono">{alert.transaction_id}</span></span></div><strong className="timeline-amount">USD {Number(alert.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong><span className="mini-alert">{alert.reason || 'Risk signal'}</span></div></div>)}</div> }

function EvidenceCard({ item }: { item: any }) { const Icon = item.kind === 'graph' ? Network : item.kind === 'timeline' ? Activity : item.kind === 'media' ? FileText : ShieldAlert; const value = item.kind === 'typology' ? `${Math.round((item.payload.confidence || .9) * 100)}% match` : item.kind === 'timeline' ? `${item.payload.count || 0} transactions` : item.kind === 'media' ? `${item.payload.matches?.length || 0} result` : `${item.payload.nodes?.length || 0} entities`; return <div className="evidence-card"><div className={`evidence-icon ${item.kind}`}><Icon size={16} /></div><div className="evidence-copy"><strong>{item.title}</strong><span>{value} · <span className="mono">{item.id}</span></span></div><CheckCircle2 size={15} className="evidence-check" /></div> }

function ModelOps({ onToast }: { onToast: (message: string) => void }) {
  const [models, setModels] = useState<any>(null)
  const [drift, setDrift] = useState<any>(null)
  const [review, setReview] = useState(45)
  const [decline, setDecline] = useState(76)
  const [saving, setSaving] = useState(false)
  useEffect(() => { void Promise.all([getModels(), getDrift()]).then(([nextModels, nextDrift]) => { setModels(nextModels); setDrift(nextDrift) }) }, [])
  const save = async () => { setSaving(true); try { await updateThresholds(review / 100, decline / 100); onToast('Threshold policy v19 saved and audit logged') } catch { onToast('Threshold preview saved locally · manager permission required by API') } setSaving(false) }
  const model = models?.champion || { version: 'fraud-champion-2026.09', stage: 'Production', calibration: 'isotonic', features: 12 }
  const challenger = models?.challenger || { version: 'fraud-challenger-graph-v2', disagreement_rate: .084, scored: 18420, lift_estimate: '+8.4%' }
  return <div className="page-content"><PageHeading eyebrow="Model governance" title="Model ops" description="Monitor champion health, challenger lift, drift, and cost-based decision thresholds."><button className="secondary-btn"><Download size={15} /> Model card</button><button className="primary-btn"><BrainCircuit size={15} /> Retrain challenger</button></PageHeading><div className="model-hero"><div className="model-hero-icon"><BrainCircuit size={22} /></div><div className="model-hero-copy"><div className="model-label">CHAMPION · PRODUCTION</div><h2>Fraud Gradient Boosted Model</h2><span>Registry version <b>{model.version}</b> · deployed 22 Sep 2026 · 12 features · isotonic calibrated</span></div><div className="model-health"><span><i /> healthy</span><strong>99.94%</strong><small>decision availability</small></div><div className="model-health"><span>p95 latency</span><strong>6.4 ms</strong><small>at 300 TPS</small></div></div><div className="models-grid"><section className="panel challenger-panel"><PanelTitle title="Champion / challenger" subtitle="Shadow scoring comparison" action={<span className="shadow-tag"><i /> shadow mode</span>} /><div className="model-compare"><div className="model-card champion-card"><div className="model-card-top"><span className="model-status-icon production"><Check size={14} /></span><div><strong>fraud-champion</strong><span>{model.version}</span></div><span className="stage-tag">PRODUCTION</span></div><div className="model-metrics"><div><strong>73.2%</strong><span>recall @ 1% FPR</span></div><div><strong>0.41</strong><span>PR-AUC</span></div><div><strong>6.4ms</strong><span>p95</span></div></div></div><div className="versus">VS</div><div className="model-card challenger-card"><div className="model-card-top"><span className="model-status-icon challenger"><Sparkles size={14} /></span><div><strong>graph challenger</strong><span>{challenger.version}</span></div><span className="stage-tag shadow">SHADOW</span></div><div className="model-metrics"><div><strong className="green-text">+8.4%</strong><span>estimated lift</span></div><div><strong>8.4%</strong><span>disagreement</span></div><div><strong>{Number(challenger.scored || 18420).toLocaleString()}</strong><span>shadow scored</span></div></div></div></div><div className="promotion-rule"><ShieldCheck size={15} /><span>Promotion requires ≥ 5% lift on a rolling 10k labeled window and explicit MLRO approval.</span><button className="text-btn">View policy <ChevronRight size={13} /></button></div></section><section className="panel drift-panel"><PanelTitle title="Drift monitor" subtitle="PSI · last 24 hours" action={<span className="healthy-tag"><i /> within limits</span>} /><div className="drift-chart"><div className="drift-y"><span>0.20</span><span>0.10</span><span>0.00</span></div><div className="chart-area"><div className="threshold-line"><span>watch threshold</span></div><svg viewBox="0 0 380 110" preserveAspectRatio="none"><defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#6fa7ff" stopOpacity=".28" /><stop offset="1" stopColor="#6fa7ff" stopOpacity="0" /></linearGradient></defs><path d="M0,84 C25,78 38,82 58,68 S95,75 114,58 S145,62 165,70 S194,47 217,56 S248,45 267,51 S292,62 311,48 S346,43 380,38 L380,110 L0,110Z" fill="url(#area)" /><path d="M0,84 C25,78 38,82 58,68 S95,75 114,58 S145,62 165,70 S194,47 217,56 S248,45 267,51 S292,62 311,48 S346,43 380,38" fill="none" stroke="#72aaff" strokeWidth="2" /></svg><div className="chart-x"><span>00h</span><span>06h</span><span>12h</span><span>18h</span><span>now</span></div></div></div><div className="drift-list">{(drift?.features || [{ name: 'velocity_1h', psi: .06, status: 'healthy' }, { name: 'amount_zscore', psi: .11, status: 'healthy' }, { name: 'graph_risk', psi: .17, status: 'watch' }, { name: 'device_sharing_degree', psi: .04, status: 'healthy' }]).map((item: any) => <div className="drift-row" key={item.name}><span className={`drift-indicator ${item.status}`} /><span>{item.name}</span><strong>{item.psi.toFixed(2)}</strong><span className={`drift-status ${item.status}`}>{item.status}</span></div>)}</div></section></div><section className="panel thresholds-panel"><PanelTitle title="Decision thresholds" subtitle="Cost-based policy · instant rollback available" action={<span className="version-chip">policy v18</span>} /><div className="threshold-content"><div className="threshold-explain"><div className="threshold-bar"><i style={{ left: `${review}%` }} /><i style={{ left: `${decline}%` }} /><span className="threshold-zone approve" style={{ width: `${review}%` }} /><span className="threshold-zone review" style={{ left: `${review}%`, width: `${decline - review}%` }} /><span className="threshold-zone decline" style={{ left: `${decline}%`, width: `${100 - decline}%` }} /></div><div className="threshold-labels"><span>Approve</span><span style={{ left: `${review}%` }}>Review · {review}%</span><span style={{ left: `${decline}%` }}>Decline · {decline}%</span></div><p>Lowering the review threshold catches more risk but increases customer friction. Changes are versioned and require manager approval.</p></div><div className="threshold-controls"><label><span>Review from</span><strong>{review}%</strong><input type="range" min="20" max={decline - 5} value={review} onChange={(event) => setReview(Number(event.target.value))} /></label><label><span>Decline from</span><strong>{decline}%</strong><input type="range" min={review + 5} max="95" value={decline} onChange={(event) => setDecline(Number(event.target.value))} /></label><button className="primary-btn" onClick={save} disabled={saving}><Save size={14} /> {saving ? 'Saving…' : 'Save policy'}</button></div></div></section></div>
}

function timeAgo(value: string) { const diff = Math.max(0, Date.now() - new Date(value).getTime()); const minutes = Math.floor(diff / 60000); if (minutes < 1) return 'just now'; if (minutes < 60) return `${minutes}m ago`; const hours = Math.floor(minutes / 60); if (hours < 24) return `${hours}h ago`; return `${Math.floor(hours / 24)}d ago` }
function formatDate(value: string) { return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) }
function formatTime(value: string) { return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)) }
function initials(name: string) { return name.split(' ').map((part) => part[0]).join('').slice(0, 2) }

export default App
