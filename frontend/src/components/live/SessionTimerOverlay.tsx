import { clsx } from 'clsx';

type SessionTimerOverlayProps = {
  phase: 'prep' | 'active';
  secondsRemaining: number;
};

export default function SessionTimerOverlay({ phase, secondsRemaining }: SessionTimerOverlayProps) {
  const isPrep = phase === 'prep';
  const urgent = !isPrep && secondsRemaining <= 3;

  return (
    <div className="pointer-events-none absolute inset-0 z-30 flex flex-col items-center justify-center bg-black/35">
      <p
        className={clsx(
          'mb-2 text-sm font-bold uppercase tracking-[0.25em]',
          isPrep ? 'text-secondary' : urgent ? 'text-error' : 'text-primary-container',
        )}
      >
        {isPrep ? 'Przygotuj się' : 'Odbijaj piłkę!'}
      </p>
      <div
        className={clsx(
          'flex h-36 w-36 items-center justify-center rounded-full border-4 shadow-2xl backdrop-blur-md',
          isPrep && 'border-secondary/60 bg-secondary/10',
          !isPrep && !urgent && 'border-primary-container/60 bg-primary-container/10 pulse-orange',
          urgent && 'border-error/70 bg-error/10 animate-pulse',
        )}
      >
        <span
          className={clsx(
            'font-display text-7xl font-bold tabular-nums',
            isPrep ? 'text-secondary' : urgent ? 'text-error' : 'text-primary-container',
          )}
        >
          {secondsRemaining}
        </span>
      </div>
      {!isPrep && (
        <p className="mt-4 max-w-xs text-center text-sm text-on-surface-variant">
          Wykonaj jak najwięcej odbić — analiza po zakończeniu odliczania
        </p>
      )}
    </div>
  );
}
