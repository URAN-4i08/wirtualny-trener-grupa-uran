import { useEffect, useState } from 'react';
import { Calendar, ChevronRight, Trash2 } from 'lucide-react';
import { clsx } from 'clsx';
import { useAuth } from '../context/AuthContext';
import {
  deleteTraining,
  fetchUserTrainings,
  formatDuration,
  formatTrainingDate,
  formatTrainingSource,
  getMainIssue,
  type TrainingWithStats,
} from '../lib/trainingData';
import { deriveElementScoresFromTraining } from '../lib/elementScores';
import ElementBars from '../components/ui/ElementBars';

export default function History() {
  const { user } = useAuth();
  const [trainings, setTrainings] = useState<TrainingWithStats[]>([]);
  const [selectedTraining, setSelectedTraining] = useState<TrainingWithStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setLoading(true);
    fetchUserTrainings(user.id)
      .then((result) => {
        if (!cancelled) {
          setTrainings(result);
          setSelectedTraining(result[0] ?? null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Nie udało się pobrać historii z bazy.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function handleDelete(trainingId: string) {
    if (!window.confirm('Usunąć ten trening z historii?')) return;
    setDeletingId(trainingId);
    try {
      await deleteTraining(trainingId);
      setTrainings((current) => current.filter((t) => t.id !== trainingId));
      setSelectedTraining((current) => (current?.id === trainingId ? null : current));
    } catch {
      setError('Nie udało się usunąć treningu.');
    } finally {
      setDeletingId(null);
    }
  }

  const selectedScores = deriveElementScoresFromTraining(selectedTraining);

  return (
    <div className="mx-auto max-w-container space-y-6">
      <header>
        <h1 className="font-display text-headline-lg text-on-surface">Historia treningów</h1>
        <p className="mt-1 text-on-surface-variant">Zapisane sesje z kamery i pliku wideo.</p>
      </header>

      {error && <div className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-error">{error}</div>}

      {loading ? (
        <div className="glass-card p-10 text-center text-on-surface-variant">Ładowanie historii...</div>
      ) : trainings.length === 0 ? (
        <div className="glass-card p-10 text-center">
          <Calendar className="mx-auto mb-4 h-10 w-10 text-primary" />
          <h2 className="font-display text-xl font-bold">Brak historii</h2>
          <p className="mt-2 text-on-surface-variant">Po zakończeniu analizy trening zapisze się automatycznie.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_340px]">
          <div className="glass-card overflow-hidden rounded-xl">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 bg-surface-container-high/40">
                    {['Data', 'Źródło', 'Czas', 'Wynik', 'Odbicia', 'Problem', ''].map((h) => (
                      <th key={h} className="px-5 py-4 font-semibold text-on-surface-variant">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trainings.map((training) => (
                    <tr
                      key={training.id}
                      className={clsx(
                        'border-b border-white/5 transition-colors hover:bg-white/5',
                        selectedTraining?.id === training.id && 'bg-primary-container/10',
                      )}
                    >
                      <td className="px-5 py-4">
                        <button
                          type="button"
                          onClick={() => setSelectedTraining(training)}
                          className="flex items-center gap-3 text-left text-on-surface"
                        >
                          <Calendar className="h-4 w-4 text-primary" />
                          {formatTrainingDate(training.start_time)}
                        </button>
                      </td>
                      <td className="px-5 py-4 text-on-surface-variant">{formatTrainingSource(training.source)}</td>
                      <td className="px-5 py-4 text-on-surface-variant">
                        {formatDuration(training.start_time, training.end_time)}
                      </td>
                      <td className="px-5 py-4">
                        <span className="rounded-full border border-success/30 bg-success/10 px-2.5 py-0.5 text-xs font-medium text-success">
                          {training.overall_score ?? 0}%
                        </span>
                      </td>
                      <td className="px-5 py-4 text-on-surface-variant">{training.stats?.total_contacts ?? 0}</td>
                      <td className="px-5 py-4 text-on-surface-variant">
                        {getMainIssue(training.stats?.posture_warnings_count)}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => setSelectedTraining(training)}
                            className="rounded-lg p-2 text-on-surface-variant hover:bg-white/5 hover:text-on-surface"
                          >
                            <ChevronRight className="h-5 w-5" />
                          </button>
                          <button
                            type="button"
                            disabled={deletingId === training.id}
                            onClick={() => void handleDelete(training.id)}
                            className="rounded-lg p-2 text-error hover:bg-error/20 disabled:opacity-50"
                          >
                            <Trash2 className="h-5 w-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="glass-card h-fit rounded-xl p-6">
            <h2 className="font-display text-lg font-bold text-on-surface">Podsumowanie serii</h2>
            {selectedTraining ? (
              <div className="mt-5 space-y-5">
                <p className="text-sm text-on-surface-variant">{formatTrainingDate(selectedTraining.start_time)}</p>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'Wynik', value: `${selectedTraining.overall_score ?? 0}%` },
                    { label: 'Odbicia', value: selectedTraining.stats?.total_contacts ?? 0 },
                    { label: 'Kąt kolan', value: `${selectedTraining.stats?.avg_knee_angle ?? 0}°` },
                    { label: 'Ostrzeżenia', value: selectedTraining.stats?.posture_warnings_count ?? 0 },
                  ].map((item) => (
                    <div key={item.label} className="rounded-lg bg-surface-container-high/60 p-3">
                      <p className="text-xs text-on-surface-variant">{item.label}</p>
                      <p className="font-display text-2xl font-bold text-on-surface">{item.value}</p>
                    </div>
                  ))}
                </div>
                <ElementBars scores={selectedScores} title="Elementy techniki" />
              </div>
            ) : (
              <p className="mt-4 text-sm text-on-surface-variant">Wybierz trening z tabeli.</p>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
