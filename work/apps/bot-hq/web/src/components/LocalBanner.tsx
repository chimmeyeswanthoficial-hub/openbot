import { useState } from 'react';
import { useStore } from '../store';
export function LocalBanner() {
  const botId = useStore(s => s.selectedBotId);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const run = async () => {
    if (!botId || busy) return;
    setBusy(true); setStatus('Checking the independent kernel…');
    try {
      const res = await fetch(`/api/bots/${encodeURIComponent(botId)}/company-report`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ requestId: crypto.randomUUID() }) });
      const data = await res.json();
      if (!res.ok || !data.receipt?.ok) throw new Error(data.error ?? data.receipt?.code ?? 'Report refused');
      setStatus(`Report saved · ${data.receipt.audit_seqs.length} kernel audit rows · recorded evidence, not a new test run`);
      await useStore.getState().loadRows(botId);
      window.dispatchEvent(new CustomEvent('grokbot:event', { detail: { type: 'tasks', botId } }));
    } catch (err) { setStatus((err as Error).message); }
    finally { setBusy(false); }
  };
  return <div className="hq-local-banner"><div><strong>OpenBot HQ</strong><span>LOCAL ONLY · ALL PROVIDERS DISABLED</span></div>
    <p role="status">{status || 'Governed company evidence, local notes and skills. No autonomous work is running.'}</p>
    <button type="button" className="btn btn--sm btn--primary" disabled={!botId || busy} onClick={() => void run()}>{busy ? 'Creating report…' : 'Run company report'}</button>
  </div>;
}
