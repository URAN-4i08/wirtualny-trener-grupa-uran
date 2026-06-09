import type { TrainingWithStats } from './trainingData';

export type ElementScores = {
  kolana: number;
  lokcie: number;
  rece: number;
  stopy: number;
  nogi: number;
};

export function kneeScoreFromAngle(angle: number | null | undefined): number {
  if (!angle || angle <= 0) return 0;
  if (angle >= 100 && angle <= 165) {
    return Math.round(72 + Math.max(0, 28 - Math.abs(angle - 135) * 0.8));
  }
  if (angle > 165) {
    return Math.round(Math.max(15, 85 - (angle - 165) * 4));
  }
  return Math.round(Math.max(25, angle * 0.55));
}

export function deriveElementScoresFromTraining(training: TrainingWithStats | null): ElementScores {
  if (!training) {
    return { kolana: 0, lokcie: 0, rece: 0, stopy: 0, nogi: 0 };
  }

  const base = training.overall_score ?? 0;
  const contact = training.stats?.avg_contact_score ?? base;
  const warnings = training.stats?.posture_warnings_count ?? 0;
  const penalty = Math.min(35, warnings * 4);

  return {
    kolana: kneeScoreFromAngle(training.stats?.avg_knee_angle) || Math.max(0, base - penalty),
    lokcie: Math.max(0, Math.min(100, contact - 5)),
    rece: Math.max(0, Math.min(100, contact)),
    stopy: Math.max(0, Math.min(100, base - Math.round(penalty * 0.6))),
    nogi: Math.max(0, Math.min(100, base - Math.round(penalty * 0.4))),
  };
}

export function aggregateElementScores(trainings: TrainingWithStats[]): ElementScores {
  if (!trainings.length) {
    return { kolana: 0, lokcie: 0, rece: 0, stopy: 0, nogi: 0 };
  }

  const totals = trainings.reduce(
    (acc, training) => {
      const scores = deriveElementScoresFromTraining(training);
      acc.kolana += scores.kolana;
      acc.lokcie += scores.lokcie;
      acc.rece += scores.rece;
      acc.stopy += scores.stopy;
      acc.nogi += scores.nogi;
      return acc;
    },
    { kolana: 0, lokcie: 0, rece: 0, stopy: 0, nogi: 0 },
  );

  const count = trainings.length;
  return {
    kolana: Math.round(totals.kolana / count),
    lokcie: Math.round(totals.lokcie / count),
    rece: Math.round(totals.rece / count),
    stopy: Math.round(totals.stopy / count),
    nogi: Math.round(totals.nogi / count),
  };
}

export const ELEMENT_LABELS: { key: keyof ElementScores; label: string; color: string }[] = [
  { key: 'kolana', label: 'Kolana', color: '#ef4444' },
  { key: 'lokcie', label: 'Łokcie', color: '#7bd0ff' },
  { key: 'rece', label: 'Ręce', color: '#d3bbff' },
  { key: 'stopy', label: 'Stopy', color: '#ffb690' },
  { key: 'nogi', label: 'Nogi', color: '#00a6e0' },
];

export function deriveElbowOk(postureWarnings: string | null | undefined): boolean {
  if (!postureWarnings) return true;
  const lower = postureWarnings.toLowerCase();
  return !lower.includes('lokcie') && !lower.includes('łokcie');
}
