import { useState } from 'react'

export function NarrativeEditor({ initialValue, onSave }: { initialValue: string; onSave: (value: string) => void }) {
  const [value, setValue] = useState(initialValue)
  return <div><textarea value={value} onChange={(event) => setValue(event.target.value)} /><button onClick={() => onSave(value)}>Save version</button></div>
}
