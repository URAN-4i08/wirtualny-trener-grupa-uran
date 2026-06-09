import { clsx } from 'clsx';

type LogoProps = {
  size?: number;
  className?: string;
  /** Pełna ikona z tłem — favicon / sidebar. Sam znak piłki bez tła — hero / dekoracje. */
  variant?: 'icon' | 'mark';
};

export default function Logo({ size = 40, className, variant = 'icon' }: LogoProps) {
  const id = `logo-${variant}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx('shrink-0', className)}
      aria-hidden
    >
      {variant === 'icon' && (
        <>
          <rect width="48" height="48" rx="11" fill="#0B1426" />
          <circle cx="24" cy="24" r="17" fill="#f97316" fillOpacity="0.1" />
        </>
      )}

      <circle cx="24" cy="24" r={variant === 'icon' ? 13 : 16} fill={`url(#${id}-ball)`} />

      <g
        stroke="#c2410c"
        strokeWidth={variant === 'icon' ? 1.75 : 2}
        strokeLinecap="round"
        fill="none"
      >
        <path d="M24 11.5c-5.5 3.5-9 7.5-9.5 12.5-.4 3.8 1.5 7.5 5 10.5" />
        <path d="M24 11.5c5.5 3.5 9 7.5 9.5 12.5.4 3.8-1.5 7.5-5 10.5" />
        <path d="M12.5 21.5c3.5 1.8 15 1.8 23 0" />
        <path d="M12.5 26.5c3.5-1.8 15-1.8 23 0" />
      </g>

      <ellipse cx="20" cy="19" rx="3.5" ry="2" fill="white" fillOpacity="0.22" transform="rotate(-25 20 19)" />

      <defs>
        <radialGradient id={`${id}-ball`} cx="38%" cy="32%" r="68%" fx="32%" fy="28%">
          <stop offset="0%" stopColor="#ffe8d9" />
          <stop offset="45%" stopColor="#ffb690" />
          <stop offset="100%" stopColor="#ea580c" />
        </radialGradient>
      </defs>
    </svg>
  );
}
