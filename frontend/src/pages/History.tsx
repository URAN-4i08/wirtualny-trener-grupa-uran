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
    setError(null);

    fetchUserTrainings(user.id)
      .then((result) => {
        if (!cancelled) setTrainings(result);
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
    const confirmed = window.confirm('Usunąć ten trening z historii? Tej operacji nie da się cofnąć.');
    if (!confirmed) return;

    setDeletingId(trainingId);
    setError(null);

    try {
      await deleteTraining(trainingId);
      setTrainings((current) => current.filter((training) => training.id !== trainingId));
      setSelectedTraining((current) => (current?.id === trainingId ? null : current));
    } catch {
      setError('Nie udało się usunąć treningu z bazy.');
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-6">
      <header>
        <h2 className="text-3xl font-bold text-white mb-2">Historia treningów</h2>
        <p className="text-on-surface-variant">Realne sesje zapisane w bazie: kamera i plik wideo razem.</p>
      </header>

      {error && (
        <div className="rounded-lg border border-error/30 bg-error/15 px-4 py-3 text-error font-medium">
          {error}
        </div>
      )}

      {loading ? (
        <div className="glass-card rounded-2xl p-8 text-on-surface-variant">Ładowanie historii...</div>
      ) : trainings.length === 0 ? (
        <div className="glass-card rounded-2xl p-8">
          <Calendar className="w-10 h-10 text-primary mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Brak historii</h3>
          <p className="text-on-surface-variant">
            Po zakończeniu analizy kamery albo pliku trening zapisze się tutaj automatycznie.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
          <div className="glass-card rounded-2xl overflow-hidden border-white/10">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[820px]">
                <thead>
                  <tr className="border-b border-white/10 bg-surface-variant/30">
                    <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Data</th>
                    <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Źródło</th>
                    <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Czas</th>
                    <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Wynik</th>
                    <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Odbicia</th>
                    <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Problem</th>
                    <th className="py-4 px-6"></th>
                  </tr>
                </thead>
                <tbody>
                  {trainings.map((training) => (
                    <tr
                      key={training.id}
                      className={clsx(
                        'border-b border-white/5 hover:bg-white/5 transition-colors group',
                        selectedTraining?.id === training.id && 'bg-primary/10',
                      )}
                    >
                      <td className="py-4 px-6">
                        <button
                          type="button"
                          onClick={() => setSelectedTraining(training)}
                          className="flex items-center gap-3 text-left text-white"
                        >
                          <div className="w-8 h-8 rounded-lg bg-surface-variant flex items-center justify-center">
                            <Calendar className="w-4 h-4 text-primary" />
                          </div>
                          {formatTrainingDate(training.start_time)}
                        </button>
                      </td>
                      <td className="py-4 px-6 text-on-surface-variant">{formatTrainingSource(training.source)}</td>
                      <td className="py-4 px-6 text-on-surface-variant">
                        {formatDuration(training.start_time, training.end_time)}
                      </td>
                      <td className="py-4 px-6">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
                          {training.overall_score ?? 0}%
                        </span>
                      </td>
                      <td className="py-4 px-6 text-on-surface-variant">{training.stats?.total_contacts ?? 0}</td>
                      <td className="py-4 px-6 text-on-surface-variant text-sm">
                        {getMainIssue(training.stats?.posture_warnings_count)}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setSelectedTraining(training)}
                            className="p-2 rounded-lg text-on-surface-variant hover:text-white hover:bg-surface-variant transition-colors"
                            title="Pokaż szczegóły"
                          >
                            <ChevronRight className="w-5 h-5" />
                          </button>
                          <button
                            type="button"
                            disabled={deletingId === training.id}
                            onClick={() => void handleDelete(training.id)}
                            className="p-2 rounded-lg text-error hover:text-white hover:bg-error/40 transition-colors disabled:opacity-50"
                            title="Usuń trening"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="glass-card rounded-2xl p-6 border-white/10 h-fit">
            <h3 className="text-lg font-bold text-white mb-4">Podsumowanie serii</h3>
            {selectedTraining ? (
              <div className="space-y-4 text-sm">
                <div>
                  <p className="text-on-surface-variant">Data</p>
                  <p className="text-white font-medium">{formatTrainingDate(selectedTraining.start_time)}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-surface-variant/40 p-3">
                    <p className="text-on-surface-variant text-xs">Wynik</p>
                    <p className="text-2xl font-bold text-white">{selectedTraining.overall_score ?? 0}%</p>
                  </div>
                  <div className="rounded-lg bg-surface-variant/40 p-3">
                    <p className="text-on-surface-variant text-xs">Odbicia</p>
                    <p className="text-2xl font-bold text-white">{selectedTraining.stats?.total_contacts ?? 0}</p>
                  </div>
                  <div className="rounded-lg bg-surface-variant/40 p-3">
                    <p className="text-on-surface-variant text-xs">Kąt kolan</p>
                    <p className="text-2xl font-bold text-white">{selectedTraining.stats?.avg_knee_angle ?? 0}°</p>
                  </div>
                  <div className="rounded-lg bg-surface-variant/40 p-3">
                    <p className="text-on-surface-variant text-xs">Ostrzeżenia</p>
                    <p className="text-2xl font-bold text-white">
                      {selectedTraining.stats?.posture_warnings_count ?? 0}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-on-surface-variant">Główny problem</p>
                  <p className="text-white font-medium">
                    {getMainIssue(selectedTraining.stats?.posture_warnings_count)}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-on-surface-variant">Wybierz trening z tabeli, żeby zobaczyć szczegóły.</p>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
