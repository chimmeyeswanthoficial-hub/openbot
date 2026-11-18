// OPENBOT-OS: licensed Lucide glyphs replace all excluded donor icon artwork.
import type { CSSProperties } from 'react';
import { ArrowDown, ArrowUp, AudioLines, Check, ChevronDown, ChevronRight, Clock, Copy, Eye, File, Grid2X2, Maximize2, MessageSquare, Mic, Minimize2, Monitor, MoreHorizontal, MousePointer2, PanelLeft, Paperclip, Pencil, Plus, RotateCw, Save, Search, Share2, Square, Star, X } from 'lucide-react';
export type IconName = 'apps' | 'arrow_down' | 'chat_filled' | 'check' | 'chev_down' | 'chev_right' | 'clock' | 'close' | 'composer_plus' | 'copy' | 'edit' | 'file' | 'mic' | 'paperclip' | 'plus' | 'record' | 'save' | 'search' | 'share' | 'sidebar' | 'slack' | 'star' | 'voice_a' | 'voice_b' | 'arrow_up' | 'stop' | 'more' | 'monitor' | 'refresh' | 'eye' | 'pointer' | 'expand' | 'shrink';
const icons = { apps: Grid2X2, arrow_down: ArrowDown, chat_filled: MessageSquare, check: Check, chev_down: ChevronDown, chev_right: ChevronRight, clock: Clock, close: X, composer_plus: Plus, copy: Copy, edit: Pencil, file: File, mic: Mic, paperclip: Paperclip, plus: Plus, record: Mic, save: Save, search: Search, share: Share2, sidebar: PanelLeft, slack: MessageSquare, star: Star, voice_a: AudioLines, voice_b: AudioLines, arrow_up: ArrowUp, stop: Square, more: MoreHorizontal, monitor: Monitor, refresh: RotateCw, eye: Eye, pointer: MousePointer2, expand: Maximize2, shrink: Minimize2 };
export function Icon({ name, size = 16, opacity, className, style, color }: { name: IconName; size?: number; opacity?: number; className?: string; style?: CSSProperties; color?: string }) {
  const Glyph = icons[name];
  return <Glyph size={size} aria-hidden className={className} color={color ?? 'currentColor'} strokeWidth={1.8} style={{ opacity, flexShrink: 0, ...style }} />;
}
