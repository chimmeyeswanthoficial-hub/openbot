// OPENBOT-OS: reuse the task/settings seam without inactive provider/computer promises.
import { useSelectedBot, useStore } from '../store';
import { BotAvatarFor } from '../avatar/BotAvatar';
import { useConfigUI } from '../configStore';
import { BotTasks } from './config/TasksView';
import { Icon } from './Icon';
export { computerStatusText } from '../lib/computer';
export function DetailsPanel() {
  const bot = useSelectedBot();
  if (!bot) return null;
  return <aside className="details" aria-label="Local workspace details">
    <div className="details__top"><button className="icon-btn" type="button" aria-label="Bot settings" onClick={() => useConfigUI.getState().openBotSettings(bot.id)}><Icon name="edit" /></button><button type="button" className="icon-btn" aria-label="Close details" onClick={() => useStore.getState().set({ detailsOpen: false })}><Icon name="close" /></button></div>
    <div className="details__scroll"><div className="details__identity"><BotAvatarFor bot={bot} size={56} /><div className="details__name">{bot.name}</div><p style={{ padding: 16, color: '#667085', lineHeight: 1.6 }}>Local notes, inert skills and audited company-readiness tasks. The independent Sentinel kernel remains the authority. No model, scheduler, screen or external account is active.</p></div><BotTasks bot={bot} /></div>
  </aside>;
}
