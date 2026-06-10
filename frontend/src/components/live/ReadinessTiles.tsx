import { CheckCircle2, XCircle } from 'lucide-react';
import { clsx } from 'clsx';
import { deriveElbowOk } from '../../lib/elementScores';

type Gotowosc = {
  stopa_ok: boolean;
  kolana_ok: boolean;
  platforma_ok: boolean;
  lokcie_ok?: boolean;
  ruch_ok: boolean;
};

type ReadinessTilesProps = {
  gotowosc?: Gotowosc | null;
  postureWarnings?: string | null;
  hasLegs?: boolean;
  compact?: boolean;
};

export default function ReadinessTiles({ gotowosc, postureWarnings, hasLegs = true, compact = false }: ReadinessTilesProps) {
  const lokcieOk =
    gotowosc?.lokcie_ok !== undefined ? gotowosc.lokcie_ok : deriveElbowOk(postureWarnings);

  const items = [
    { label: 'Stopy', ok: hasLegs ? gotowosc?.stopa_ok : false },
    { label: 'Kolana', ok: hasLegs ? gotowosc?.kolana_ok : false },
    { label: 'Łokcie', ok: gotowosc ? lokcieOk : undefined },
    { label: 'Ręce', ok: gotowosc?.platforma_ok },
    { label: 'W kadrze', ok: hasLegs ? gotowosc?.ruch_ok : false },
  ];

  if (compact) {
    return (
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <div
            key={item.label}
            title={item.label}
            className={clsx(
              'flex h-11 w-11 items-center justify-center rounded-lg border',
              item.ok === true && 'border-success/40 bg-success/80 text-white',
              item.ok === false && 'border-error/40 bg-error/80 text-white',
              item.ok === undefined && 'border-white/10 bg-surface-container-highest text-on-surface-variant',
            )}
          >
            {item.ok === true ? <CheckCircle2 className="h-5 w-5" /> : item.ok === false ? <XCircle className="h-5 w-5" /> : '—'}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-on-surface-variant">Gotowość segmentów</p>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.label}
            className={clsx(
              'flex items-center justify-between rounded-lg border-l-4 bg-white/5 px-3 py-2.5',
              item.ok === true && 'border-success',
              item.ok === false && 'border-error',
              item.ok === undefined && 'border-outline-variant',
            )}
          >
            <span className="text-sm text-on-surface">{item.label}</span>
            {item.ok === true ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : item.ok === false ? (
              <XCircle className="h-5 w-5 text-error" />
            ) : (
              <span className="text-xs text-on-surface-variant">—</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
