import { useEffect, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';
import ReadinessTiles from './ReadinessTiles';

type Gotowosc = {
  stopa_ok: boolean;
  kolana_ok: boolean;
  platforma_ok: boolean;
  ruch_ok: boolean;
};

type FollowThroughOverlayProps = {
  feedback: string;
  score: number;
  gotowosc?: Gotowosc | null;
  postureWarnings?: string | null;
};

export default function FollowThroughOverlay({
  feedback,
  score,
  gotowosc,
  postureWarnings,
}: FollowThroughOverlayProps) {
  const [countdown, setCountdown] = useState(3);
  const isPositive = feedback.includes('✓') || feedback.toLowerCase().includes('dobre');

  useEffect(() => {
    setCountdown(3);
    const timer = window.setInterval(() => {
      setCountdown((value) => (value > 1 ? value - 1 : 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [feedback]);

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/60 p-4 md:p-8">
      <div className="flex w-full max-w-3xl flex-col items-center gap-6">
        <div className="text-center">
          <p className="font-display text-5xl font-bold text-primary drop-shadow-orange-glow md:text-6xl">
            {countdown > 0 ? countdown : '·'}
          </p>
          <p className="mt-2 text-sm font-semibold uppercase tracking-[0.2em] text-secondary">Podejdź do ekranu</p>
        </div>

        <div className="glass-panel w-full rounded-2xl p-6 shadow-orange-glow md:p-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-start">
            <div className="flex-1">
              <h2 className="font-display text-headline-md text-on-surface">Podsumowanie odbicia</h2>
              <div className={clsx('mt-3 flex items-start gap-2', isPositive ? 'text-secondary' : 'text-error')}>
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
                <p className="text-lg font-medium leading-snug">{feedback}</p>
              </div>
              <div className="mt-6">
                <ReadinessTiles gotowosc={gotowosc} postureWarnings={postureWarnings} compact />
              </div>
            </div>
            <div className="flex flex-col items-center justify-center border-t border-white/10 pt-6 md:min-w-[160px] md:border-l md:border-t-0 md:pl-8 md:pt-0">
              <span className="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">Wynik ogólny</span>
              <p className="font-display text-kpi-value text-primary">{score}/100</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
