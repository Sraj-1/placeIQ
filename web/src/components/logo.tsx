// PlaceIQ mark: a readiness gauge with a rising needle, on the brand tile.
export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" className="fill-brand" />
      <path d="M7.5 21.5a8.5 8.5 0 0 1 17 0" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" className="text-brand-foreground" />
      <path d="M16 21.5l4.6-6.4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" className="text-brand-foreground" />
      <circle cx="16" cy="21.5" r="2.1" className="fill-brand-foreground" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="leading-none">
        <span className="block font-display text-[22px] tracking-tight text-headline">PlaceIQ</span>
        <span className="mt-0.5 block text-[10px] font-medium uppercase tracking-[0.16em] text-faint">Placement readiness</span>
      </span>
    </span>
  );
}
