import { clsx } from 'clsx';
import ReadinessTiles from './ReadinessTiles';
import { deriveElbowOk } from '../../lib/elementScores';

type Gotowosc = {
  stopa_ok: boolean;
  kolana_ok: boolean;
  platforma_ok: boolean;
  lokcie_ok?: boolean;
  ruch_ok: boolean;
};

type SessionSetupOverlayProps = {
  gotowosc?: Gotowosc | null;
  postureWarnings?: string | null;
  hasLegs?: boolean;
  hasPose?: boolean;
  almostReady?: boolean;
};

function countReadySegments(gotowosc: Gotowosc | null | undefined, postureWarnings?: string | null, hasLegs = true) {
  if (!gotowosc || !hasLegs) return 0;
  let count = 0;
  if (gotowosc.stopa_ok) count += 1;
  if (gotowosc.kolana_ok) count += 1;
  if (gotowosc.lokcie_ok !== undefined ? gotowosc.lokcie_ok : deriveElbowOk(postureWarnings)) count += 1;
  if (gotowosc.platforma_ok) count += 1;
  if (gotowosc.ruch_ok) count += 1;
  return count;
}

export default function SessionSetupOverlay({
  gotowosc,
  postureWarnings,
  hasLegs = true,
  hasPose = false,
  almostReady = false,
}: SessionSetupOverlayProps) {
  const readyCount = countReadySegments(gotowosc, postureWarnings, hasLegs);

  return (
    <div className="pointer-events-none absolute inset-0 z-30 flex flex-col items-center justify-center bg-black/30 p-4">
      <div className="glass-panel max-w-md rounded-2xl px-6 py-5 text-center shadow-lg">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-secondary">Krok 1 — ustawienie</p>
        <h2 className="mt-2 font-display text-xl font-bold text-on-surface md:text-2xl">
          {!hasPose ? 'Stań w kadrze kamery' : 'Ustaw postawę startową'}
        </h2>
        <p className="mt-2 text-sm text-on-surface-variant">
          {almostReady
            ? 'Świetnie! Odliczanie zaraz wystartuje...'
            : 'Wszystkie segmenty poniżej muszą być zielone — wtedy zacznie się odliczanie 3 s.'}
        </p>
        <p className="mt-3 font-display text-3xl font-bold text-primary-container">
          {readyCount}/5
        </p>
        <div className="mt-4 flex justify-center">
          <ReadinessTiles gotowosc={gotowosc} postureWarnings={postureWarnings} hasLegs={hasLegs} compact />
        </div>
        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
          <div
            className={clsx('h-full transition-all', almostReady ? 'bg-success' : 'bg-primary-container')}
            style={{ width: `${(readyCount / 5) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
