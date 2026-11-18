// OPENBOT-OS: new neutral letter badges; no donor silhouettes, eyes or generated paths.
import type { AvatarColor, AvatarShape, Bot } from '@shared/types';
import { palette } from '../lib/colors';

export const PICKER_SHAPES: AvatarShape[] = ['square', 'tablet', 'capsule'];
interface Props { shape: AvatarShape | string; color: AvatarColor | string; size: number; star?: boolean; ring?: boolean; className?: string; title?: string }
export function BotAvatar({ shape, color, size, star, ring, className, title }: Props) {
  const rounded = shape === 'capsule' ? '50%' : shape === 'tablet' ? '32%' : '20%';
  return <span className={`bot-avatar ${className ?? ''}`} role="img" aria-label={title ?? 'Local bot'} title={title}
    style={{ width: size, height: size, borderRadius: rounded, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      background: palette(color).fill, color: '#fff', fontSize: size * .43, fontWeight: 650, lineHeight: 1,
      outline: ring ? '2px solid #667085' : undefined, outlineOffset: ring ? 3 : undefined }}>
    {(title?.trim()[0] ?? 'B').toUpperCase()}{star && <span style={{ position: 'absolute', right: -2, bottom: -2, fontSize: size * .23, color: '#fff', background: '#243b53', borderRadius: '50%', padding: 2 }}>•</span>}
  </span>;
}
export function BotAvatarFor({ bot, size, star, className }: { bot: Pick<Bot, 'avatarShape' | 'avatarColor' | 'name'> & { isPrimary?: boolean }; size: number; star?: boolean; className?: string }) {
  return <BotAvatar shape={bot.avatarShape} color={bot.avatarColor} title={bot.name} size={size} star={star} className={className} />;
}
