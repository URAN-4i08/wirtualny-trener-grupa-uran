import { supabase } from '../config/supabase';

export type TrainingSource = 'camera' | 'file' | string;

export type TrainingStats = {
  id: string;
  training_id: string;
  total_contacts: number | null;
  avg_knee_angle: number | null;
  posture_warnings_count: number | null;
  avg_contact_score: number | null;
};

export type Training = {
  id: string;
  user_id: string;
  start_time: string;
  end_time: string | null;
  source: TrainingSource | null;
  overall_score: number | null;
  status: string | null;
  training_stats?: TrainingStats[] | TrainingStats | null;
};

export type TrainingWithStats = Training & {
  stats: TrainingStats | null;
};

type TrainingRow = Training & {
  training_stats?: TrainingStats[] | TrainingStats | null;
};

export function normalizeTraining(row: TrainingRow): TrainingWithStats {
  const rawStats = row.training_stats;
  const stats = Array.isArray(rawStats) ? rawStats[0] ?? null : rawStats ?? null;
  return { ...row, stats };
}

export async function fetchUserTrainings(userId: string): Promise<TrainingWithStats[]> {
  const { data, error } = await supabase
    .from('trainings')
    .select('*, training_stats(*)')
    .eq('user_id', userId)
    .order('start_time', { ascending: false });

  if (error) throw error;
  return ((data ?? []) as TrainingRow[]).map(normalizeTraining);
}

export async function deleteTraining(trainingId: string) {
  const statsDelete = await supabase.from('training_stats').delete().eq('training_id', trainingId);
  if (statsDelete.error) throw statsDelete.error;

  const trainingDelete = await supabase.from('trainings').delete().eq('id', trainingId);
  if (trainingDelete.error) throw trainingDelete.error;
}

export function formatTrainingSource(source: TrainingSource | null | undefined) {
  if (source === 'camera') return 'kamera';
  if (source === 'file') return 'plik wideo';
  return 'nieznane';
}

export function formatDuration(startTime: string, endTime: string | null) {
  if (!endTime) return 'w trakcie';

  const start = new Date(startTime).getTime();
  const end = new Date(endTime).getTime();
  const diffSeconds = Math.max(0, Math.round((end - start) / 1000));
  const minutes = Math.floor(diffSeconds / 60);
  const seconds = diffSeconds % 60;

  if (minutes <= 0) return `${seconds} s`;
  if (seconds === 0) return `${minutes} min`;
  return `${minutes} min ${seconds} s`;
}

export function formatTrainingDate(date: string) {
  return new Intl.DateTimeFormat('pl-PL', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function getMainIssue(warningsCount: number | null | undefined) {
  if ((warningsCount ?? 0) > 0) return 'Postawa do poprawy';
  return 'Brak głównego problemu';
}
