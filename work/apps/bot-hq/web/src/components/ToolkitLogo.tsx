// OPENBOT-OS: no provider logos, remote image requests or trademarks in this derivative.
export function ToolkitLogo({ name, size = 40, radius = 8 }: { name: string; logo?: string; size?: number; radius?: number }) {
  return <span className="toolkit-logo" style={{ width: size, height: size, borderRadius: radius }}>
    <span className="toolkit-logo__letter" style={{ fontSize: size * .42 }}>{(name.trim()[0] ?? '?').toUpperCase()}</span>
  </span>;
}
