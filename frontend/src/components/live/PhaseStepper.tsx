import { clsx } from 'clsx';

const PHASES = [
  { id: 'OCZEKIWANIE', label: 'Oczekiwanie' },
  { id: 'PRZYGOTOWANIE', label: 'Przygotowanie' },
  { id: 'KONTAKT', label: 'Kontakt' },
  { id: 'FOLLOW_THROUGH', label: 'Podsumowanie' },
] as const;

type PhaseId = (typeof PHASES)[number]['id'];

export default function PhaseStepper({ current }: { current?: PhaseId | string | null }) {
  const activeIndex = PHASES.findIndex((p) => p.id === current);

  return (
    <div className="glass-panel flex items-center justify-between gap-2 rounded-xl px-4 py-3 overflow-x-auto scrollbar-hide">
      {PHASES.map((phase, index) => {
        const isActive = index === activeIndex;
        const isPast = activeIndex > index;

        return (
          <div key={phase.id} className="flex flex-1 items-center gap-2 min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <div
                className={clsx(
                  'flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-display text-sm font-bold',
                  isActive && 'bg-primary-container text-on-primary-container ring-4 ring-primary-container/25',
                  isPast && !isActive && 'bg-success/20 text-success',
                  !isActive && !isPast && 'border-2 border-outline-variant text-on-surface-variant',
                )}
              >
                {index + 1}
              </div>
              <span
                className={clsx(
                  'hidden truncate text-xs font-semibold uppercase tracking-wide sm:inline',
                  isActive ? 'text-primary' : 'text-on-surface-variant',
                )}
              >
                {phase.label}
              </span>
            </div>
            {index < PHASES.length - 1 && <div className="mx-1 h-px flex-1 bg-white/10 min-w-[12px]" />}
          </div>
        );
      })}
    </div>
  );
}
