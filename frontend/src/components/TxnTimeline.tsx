export function TxnTimeline({ transactions }: { transactions: Array<{ id?: string; amount?: number }> }) {
  return <ol aria-label="Transaction timeline">{transactions.map((transaction, index) => <li key={transaction.id || index}>{transaction.amount ?? 0}</li>)}</ol>
}
