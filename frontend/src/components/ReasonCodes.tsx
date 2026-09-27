import type { ReasonCode } from '../api/client'

export function ReasonCodes({ reasons }: { reasons: ReasonCode[] }) {
  return <ul aria-label="SHAP reason codes">{reasons.map((reason) => <li key={reason.code}>{reason.label}: {reason.contribution.toFixed(2)}</li>)}</ul>
}
