import { CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';
import ReadinessTiles from './ReadinessTiles';

type SessionSummary = {
  count: number;
  avgScore: number;
  bestScore: number;
  feedback: string;
  gotowosc?: {
    stopa_ok: boolean;
    kolana_ok: boolean;
    platforma_ok: boolean;
    ruch_ok: boolean;
  } | null;
};

type SessionSummaryOverlayProps = {
  summary: SessionSummary;
};

export default function SessionSummaryOverlay({ summary }: SessionSummaryOverlayProps) {
  const isPositive = summary.avgScore >= 70 || summary.feedback.includes('✓');

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/65 p-4 md:p-8">
      <div className="glass-panel w-full max-w-3xl rounded-2xl p-6 shadow-orange-glow md:p-8">
        <p className="text-center text-xs font-bold uppercase tracking-[0.2em] text-secondary">Analiza sesji</p>
        <h2 className="mt-2 text-center font-display text-2xl font-bold text-on-surface md:text-3xl">
          {summary.count} {summary.count === 1 ? 'odbicie' : 'odbić'} w 10 sekund
        </h2>

        <div className="mt-6 flex flex-col gap-6 md:flex-row md:items-start">
          <div className="flex-1">
            <div className={clsx('flex items-start gap-2', isPositive ? 'text-secondary' : 'text-primary-container')}>
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
              <p className="text-lg font-medium leading-snug">{summary.feedback}</p>
            </div>
            <div className="mt-6">
              <ReadinessTiles gotowosc={summary.gotowosc} hasLegs={Boolean(summary.gotowosc)} compact />
            </div>
          </div>
          <div className="flex flex-col items-center justify-center gap-4 border-t border-white/10 pt-6 md:min-w-[180px] md:border-l md:border-t-0 md:pl-8 md:pt-0">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">Średnia ocena</span>
              <p className="font-display text-5xl font-bold text-primary">{summary.avgScore}</p>
            </div>
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">Najlepsze odbicie</span>
              <p className="font-display text-2xl font-bold text-secondary">{summary.bestScore}/100</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
