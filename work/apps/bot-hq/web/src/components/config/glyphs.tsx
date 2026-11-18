// OPENBOT-OS: licensed Lucide glyphs; no retained design-export paths.
import type { CSSProperties } from 'react';
import { ArrowLeft, CircleCheck, Download, FileText, Folder, ListChecks, Play, Settings, Sparkles, Trash2 } from 'lucide-react';
const icons = { trash: Trash2, download: Download, folder: Folder, doc: FileText, gear: Settings, play: Play, check_circle: CircleCheck, spark: Sparkles, arrow_left: ArrowLeft, tasks: ListChecks };
export type GlyphName = keyof typeof icons;
export function Glyph({ name, size = 16, opacity, style, className }: { name: GlyphName; size?: number; opacity?: number; style?: CSSProperties; className?: string }) {
  const Component = icons[name];
  return <Component className={className} size={size} aria-hidden strokeWidth={1.8} style={{ opacity, flexShrink: 0, ...style }} />;
}
