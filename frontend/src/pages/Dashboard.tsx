import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Activity, BarChart3, Target, TrendingUp, Volleyball } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { useAuth } from '../context/AuthContext';
import {
  fetchUserTrainings,
  formatDuration,
  formatTrainingDate,
  formatTrainingSource,
  getMainIssue,
  type TrainingWithStats,
} from '../lib/trainingData';

type DashboardStats = {
  trainingCount: number;
  averageScore: number;
  bestScore: number;
  totalContacts: number;
  totalWarnings: number;
  lastTraining: TrainingWithStats | null;
};

function calculateStats(trainings: TrainingWithStats[]): DashboardStats {
  const trainingCount = trainings.length;
  const scores = trainings.map((training) => training.overall_score ?? 0);
  const totalScore = scores.reduce((sum, score) => sum + score, 0);
  const totalContacts = trainings.reduce((sum, training) => sum + (training.stats?.total_contacts ?? 0), 0);
  const totalWarnings = trainings.reduce((sum, training) => sum + (training.stats?.posture_warnings_count ?? 0), 0);

  return {
    trainingCount,
    averageScore: trainingCount ? Math.round(totalScore / trainingCount) : 0,
    bestScore: scores.length ? Math.max(...scores) : 0,
    totalContacts,
    totalWarnings,
    lastTraining: trainings[0] ?? null,
  };
}

export default function Dashboard() {
  const { user, displayName } = useAuth();
  const [trainings, setTrainings] = useState<TrainingWithStats[]>([]);
  const [loading, setLoading] = useState(true);
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
        if (!cancelled) setError('Nie udało się pobrać statystyk z bazy.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user]);

  const stats = useMemo(() => calculateStats(trainings), [trainings]);
  const pieData = [
    { name: 'Wynik', value: stats.averageScore, color: '#4ade80' },
    { name: 'Do poprawy', value: 100 - stats.averageScore, color: '#32353c' },
  ];

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-8 pb-10">
      <header>
        <h2 className="text-3xl font-bold text-white mb-2">Cześć, {displayName}</h2>
        <p className="text-on-surface-variant">Tutaj zobaczysz postęp i statystyki zapisane w bazie.</p>
      </header>

      {error && (
        <div className="rounded-lg border border-error/30 bg-error/15 px-4 py-3 text-error font-medium">
          {error}
        </div>
      )}

      {loading ? (
        <div className="glass-card rounded-2xl p-8 text-on-surface-variant">Ładowanie statystyk...</div>
      ) : trainings.length === 0 ? (
        <div className="glass-card rounded-2xl p-8">
          <Activity className="w-10 h-10 text-primary mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Brak zapisanych treningów</h3>
          <p className="text-on-surface-variant">
            Po pierwszej analizie kamery albo pliku pojawią się tutaj realne statystyki.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-sm font-medium text-on-surface-variant">Treningi</h3>
                <Activity className="w-5 h-5 text-primary" />
              </div>
              <div className="text-3xl font-bold text-white">{stats.trainingCount}</div>
            </div>

            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-sm font-medium text-on-surface-variant">Średni wynik</h3>
                <BarChart3 className="w-5 h-5 text-primary" />
              </div>
              <div className="text-3xl font-bold text-white">{stats.averageScore}%</div>
            </div>

            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-sm font-medium text-on-surface-variant">Najlepszy wynik</h3>
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <div className="text-3xl font-bold text-white">{stats.bestScore}%</div>
            </div>

            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-sm font-medium text-on-surface-variant">Odbicia</h3>
                <Volleyball className="w-5 h-5 text-primary" />
              </div>
              <div className="text-3xl font-bold text-white">{stats.totalContacts}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="glass-card rounded-2xl p-6 flex flex-col">
              <h3 className="text-lg font-medium text-on-surface-variant mb-2">Skuteczność serii</h3>
              <div className="flex-1 flex items-center justify-center relative min-h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={55} outerRadius={78} paddingAngle={4} dataKey="value" stroke="none">
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center flex-col">
                  <span className="text-3xl font-bold text-white">{stats.averageScore}%</span>
                  <span className="text-xs text-on-surface-variant">średnio</span>
                </div>
              </div>
            </div>

            <div className="glass-card rounded-2xl p-6">
              <h3 className="text-lg font-medium text-on-surface-variant mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-primary" />
                Ostatni trening
              </h3>
              {stats.lastTraining && (
                <div className="space-y-3 text-sm">
                  <p className="text-white font-bold">{formatTrainingDate(stats.lastTraining.start_time)}</p>
                  <p className="text-on-surface-variant">Źródło: {formatTrainingSource(stats.lastTraining.source)}</p>
                  <p className="text-on-surface-variant">
                    Czas: {formatDuration(stats.lastTraining.start_time, stats.lastTraining.end_time)}
                  </p>
                  <p className="text-on-surface-variant">Wynik: {stats.lastTraining.overall_score ?? 0}%</p>
                  <p className="text-on-surface-variant">
                    Odbicia: {stats.lastTraining.stats?.total_contacts ?? 0}
                  </p>
                </div>
              )}
            </div>

            <div className="glass-card rounded-2xl p-6">
              <h3 className="text-lg font-medium text-on-surface-variant mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-primary" />
                Do poprawy
              </h3>
              <div className="bg-surface-variant/40 rounded-lg p-4 border border-white/5">
                <p className="text-sm text-white font-medium mb-1">{getMainIssue(stats.totalWarnings)}</p>
                <p className="text-xs text-on-surface-variant">
                  Liczba ostrzeżeń postawy we wszystkich treningach: {stats.totalWarnings}.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
