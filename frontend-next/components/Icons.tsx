interface IconProps {
  className?: string;
}

const base = "h-4 w-4 shrink-0";

export function TableIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`${base} ${className}`}>
      <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M1.5 6.2h13M6.2 6.2v7.3" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function SigmaIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`${base} ${className}`}>
      <path
        d="M11.5 3.2H4.6l3.7 4.8-3.7 4.8h6.9"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LinkIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`${base} ${className}`}>
      <circle cx="4" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="12" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.2" />
      <path d="M6.2 8h3.6" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function ChevronIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`h-3 w-3 shrink-0 ${className}`}>
      <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function CopyIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`h-3.5 w-3.5 shrink-0 ${className}`}>
      <rect x="5.5" y="5.5" width="8" height="8" rx="1.4" stroke="currentColor" strokeWidth="1.2" />
      <path d="M10.5 5.5v-1a1.4 1.4 0 00-1.4-1.4H3.9A1.4 1.4 0 002.5 4.5v5.2a1.4 1.4 0 001.4 1.4h1" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function CheckIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`h-3.5 w-3.5 shrink-0 ${className}`}>
      <path d="M3.5 8.4l3 3 6-6.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SearchIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`h-3.5 w-3.5 shrink-0 ${className}`}>
      <circle cx="7.2" cy="7.2" r="4" stroke="currentColor" strokeWidth="1.3" />
      <path d="M10.2 10.2l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export function SendIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`${base} ${className}`}>
      <path d="M2.6 8h9.2M8.4 4.4L12 8l-3.6 3.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function WarnIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={`${base} ${className}`}>
      <path d="M8 2.8l5.6 9.7H2.4L8 2.8z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      <path d="M8 6.6v2.6M8 10.9v.1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
