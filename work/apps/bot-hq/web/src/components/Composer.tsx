// OPENBOT-OS: local notes only. No microphone, dictation or call modules loaded here.
import { useEffect, useState } from 'react';
import type { Bot } from '@shared/types';
import { api } from '../lib/api';
import { useStore } from '../store';
import { Icon } from './Icon';
export function Composer({ bot }: { bot: Bot; running: boolean }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setNote(''); setError(''); }, [bot.id]);
  const save = async () => {
    if (!note.trim() || busy) return;
    setBusy(true); setError('');
    try { await api.send(bot.id, note.trim()); setNote(''); await useStore.getState().loadRows(bot.id); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  return <div className="composer-area">
    <div style={{ fontSize: 12, color: '#667085', padding: '0 16px 8px' }}>Notes are stored locally. No live AI agent is attached.</div>
    {error && <div className="composer__error" role="alert">{error}</div>}
    <div className="composer"><div className="composer__left" style={{ flex: 1 }}>
      <textarea className="composer__input" rows={2} value={note} maxLength={16000} placeholder={`Save a local note for ${bot.name}`} aria-label="Local note" onChange={e => setNote(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void save(); } }} />
    </div><div className="composer__right"><button className="composer__cta" type="button" disabled={busy || !note.trim()} aria-label="Save note" title="Save note" onClick={() => void save()}><Icon name="save" /></button></div></div>
  </div>;
}
