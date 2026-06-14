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
    { label: 'Stopy', desc: 'rozstaw ok. na szerokość bioder', ok: hasLegs ? gotowosc?.stopa_ok : false },
    { label: 'Kolana', desc: 'lekko ugięte (pozycja gotowości)', ok: hasLegs ? gotowosc?.kolana_ok : false },
    { label: 'Łokcie', desc: 'przedramiona przed sobą', ok: gotowosc ? lokcieOk : undefined },
    { label: 'Ręce', desc: 'dłonie złączone — platforma', ok: gotowosc?.platforma_ok },
    { label: 'W kadrze', desc: 'cała sylwetka widoczna', ok: hasLegs ? gotowosc?.ruch_ok : false },
  ];

  if (compact) {
    return (
      <div className="flex flex-wrap justify-center gap-2">
        {items.map((item) => (
          <div key={item.label} className="flex w-16 flex-col items-center gap-1" title={item.desc}>
            <div
              className={clsx(
                'flex h-11 w-11 items-center justify-center rounded-lg border',
                item.ok === true && 'border-success/40 bg-success/80 text-white',
                item.ok === false && 'border-error/40 bg-error/80 text-white',
                item.ok === undefined && 'border-white/10 bg-surface-container-highest text-on-surface-variant',
              )}
            >
              {item.ok === true ? <CheckCircle2 className="h-5 w-5" /> : item.ok === false ? <XCircle className="h-5 w-5" /> : '—'}
            </div>
            <span className="text-center text-[10px] font-semibold leading-tight text-on-surface-variant">{item.label}</span>
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
              'flex items-center justify-between rounded-lg border-l-4 bg-white/5 px-3 py-2',
              item.ok === true && 'border-success',
              item.ok === false && 'border-error',
              item.ok === undefined && 'border-outline-variant',
            )}
          >
            <div className="min-w-0">
              <span className="text-sm font-medium text-on-surface">{item.label}</span>
              <span className="block truncate text-xs text-on-surface-variant">{item.desc}</span>
            </div>
            {item.ok === true ? (
              <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
            ) : item.ok === false ? (
              <XCircle className="h-5 w-5 shrink-0 text-error" />
            ) : (
              <span className="text-xs text-on-surface-variant">—</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
