import type { ElementScores } from '../../lib/elementScores';
import { ELEMENT_LABELS } from '../../lib/elementScores';

export default function ElementBars({ scores, title }: { scores: ElementScores; title?: string }) {
  return (
    <div className="space-y-4">
      {title && <h3 className="font-display text-headline-md text-on-surface">{title}</h3>}
      {ELEMENT_LABELS.map(({ key, label, color }) => (
        <div key={key} className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-on-surface-variant">{label}</span>
            <span className="font-medium text-on-surface">{scores[key]}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${scores[key]}%`, backgroundColor: color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
