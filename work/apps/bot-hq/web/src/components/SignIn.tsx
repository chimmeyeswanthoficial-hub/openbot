// OPENBOT-OS: explicit local access, no Google/Composio/OAuth or provider credentials.
import { useState } from 'react';
import { BotAvatar } from '../avatar/BotAvatar';
import { useStore } from '../store';

export function SignIn() {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const checkAuth = useStore(s => s.checkAuth);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const res = await fetch('/api/auth/local', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) });
      if (!res.ok) throw new Error((await res.json()).error ?? 'Local sign-in failed');
      setCode(''); await checkAuth();
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  };
  return <div className="signin"><div className="signin__card">
    <div className="signin__hero"><BotAvatar shape="square" color="blue" size={72} title="OpenBot HQ" /></div>
    <h1 className="signin__title">OpenBot HQ</h1>
    <p className="signin__sub">Installed local workspace. All AI providers, computer control, voice, payments and outbound actions are disabled.</p>
    <form className="signin__dev" onSubmit={submit}>
      <label htmlFor="local-code">Local access code</label>
      <input id="local-code" className="text-input" type="password" autoComplete="off" value={code} onChange={e => setCode(e.target.value)} required maxLength={256} />
      <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? 'Opening…' : 'Open local workspace'}</button>
    </form>
    {error && <p className="card__error" role="alert">{error}</p>}
    <p className="signin__foot">Get the code on the host: <code>bash scripts/bot-hq.sh access-code</code><br />Bot HQ MIT code by Nick Vasilescu. Local derivative; not affiliated with xAI.</p>
  </div></div>;
}
